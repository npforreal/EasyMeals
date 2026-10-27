import SwiftUI

public struct AddPantrySheet: View {
    @Environment(\.dismiss) private var dismiss
    var storage = AppStorage.shared

    @State private var searchText = ""
    @State private var selectedIngredient: Ingredient?
    @State private var quantityText = "200"
    @State private var unit = "g"
    @State private var selectedExpiryDays: Int? = 3

    private let availableUnits = ["g", "kg", "ml", "l", "piece"]

    var filteredIngredients: [Ingredient] {
        if searchText.isEmpty {
            return Array(storage.ingredients.prefix(15))
        }
        return storage.ingredients.filter {
            CatalogueLoader.matches(text: $0.name, query: searchText)
        }
    }

    // Các món hay dùng / mua gần đây
    var recentIngredients: [Ingredient] {
        let recentNames = Set(storage.pantryLots.prefix(8).map { $0.ingredientName })
        return storage.ingredients.filter { recentNames.contains($0.name) }
    }

    public var body: some View {
        NavigationStack {
            Form {
                Section("1. Chọn nguyên liệu") {
                    TextField("Tìm nguyên liệu (ví dụ: ba chỉ, rau muống...)", text: $searchText)
                        .autocorrectionDisabled()

                    if selectedIngredient == nil {
                        if !recentIngredients.isEmpty && searchText.isEmpty {
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    ForEach(recentIngredients) { ing in
                                        Button {
                                            select(ingredient: ing)
                                        } label: {
                                            Text(ing.name)
                                                .font(.caption)
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 6)
                                                .background(AppColors.primaryLight.opacity(0.4))
                                                .foregroundColor(AppColors.primary)
                                                .cornerRadius(12)
                                        }
                                    }
                                }
                                .padding(.vertical, 4)
                            }
                        }

                        List(filteredIngredients.prefix(10)) { ing in
                            Button {
                                select(ingredient: ing)
                            } label: {
                                HStack {
                                    Text(ing.name)
                                        .foregroundColor(AppColors.textPrimary)
                                    Spacer()
                                    Text(GeneratedTokens.Labels.ingredient_categories[ing.category] ?? ing.category)
                                        .font(.caption2)
                                        .foregroundColor(AppColors.textSecondary)
                                }
                            }
                        }
                    } else if let sel = selectedIngredient {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(sel.name)
                                    .font(.headline)
                                    .foregroundColor(AppColors.primary)
                                Text("Đã chọn")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            Button("Đổi") {
                                selectedIngredient = nil
                            }
                            .font(.subheadline)
                        }
                    }
                }

                Section("2. Định lượng & Đơn vị") {
                    HStack {
                        TextField("Số lượng", text: $quantityText)
                            .keyboardType(.decimalPad)
                            .font(.title3.bold())

                        Picker("Đơn vị", selection: $unit) {
                            ForEach(availableUnits, id: \.self) { u in
                                Text(u).tag(u)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                }

                Section("3. Hạn sử dụng") {
                    HStack(spacing: 8) {
                        expiryButton(label: "3 ngày", days: 3)
                        expiryButton(label: "1 tuần", days: 7)
                        expiryButton(label: "2 tuần", days: 14)
                        expiryButton(label: "Không hạn", days: nil)
                    }
                }
            }
            .navigationTitle("Thêm vào tủ")
            .navigationBarTitleDisplayMode(.inline)
            .safeAreaInset(edge: .bottom) {
                Button {
                    save()
                } label: {
                    Text("Lưu một chạm")
                        .font(.headline.bold())
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(selectedIngredient != nil && !quantityText.isEmpty ? AppColors.primary : Color.gray.opacity(0.4))
                        .cornerRadius(14)
                }
                .disabled(selectedIngredient == nil || quantityText.isEmpty)
                .padding(.horizontal, 20)
                .padding(.bottom, 8)
                .background(AppColors.surface)
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Hủy") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Lưu một chạm") {
                        save()
                    }
                    .bold()
                    .disabled(selectedIngredient == nil || quantityText.isEmpty)
                }
            }
        }
    }

    private func sensibleDefaultQuantity(for ing: Ingredient) -> String {
        let unit = ing.defaultUnit
        let cat = ing.category
        let name = ing.name.lowercased()
        switch unit {
        case "piece":
            if name.contains("trứng") { return "6" }
            if name.contains("đậu hũ") || name.contains("tàu hũ") { return "2" }
            return "1"
        case "kg", "l":
            return "1"
        case "ml":
            return cat == "nuoc_cham_dau" ? "100" : "200"
        default:
            switch cat {
            case "thit", "gia_cam", "hai_san": return "400"
            case "rau_cu", "cu_qua": return "300"
            case "gao_bot_mi": return "500"
            case "gia_vi": return "30"
            case "nuoc_cham_dau": return "100"
            default: return "200"
            }
        }
    }

    private func select(ingredient: Ingredient) {
        self.selectedIngredient = ingredient
        self.unit = ingredient.defaultUnit
        self.quantityText = sensibleDefaultQuantity(for: ingredient)
        self.searchText = ingredient.name
        // Hạn mặc định theo nhóm nguyên liệu (từ GeneratedTokens / design-tokens/labels.json)
        if let daysStr = GeneratedTokens.Labels.default_expiry_days[ingredient.category ?? "khac"],
           daysStr != "None", let days = Int(daysStr) {
            self.selectedExpiryDays = days
        } else {
            self.selectedExpiryDays = nil // "Không hạn"
        }
    }

    private func expiryButton(label: String, days: Int?) -> some View {
        Button {
            selectedExpiryDays = days
        } label: {
            Text(label)
                .font(.caption.bold())
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
                .background(selectedExpiryDays == days ? AppColors.primary : AppColors.secondarySurface)
                .foregroundColor(selectedExpiryDays == days ? .white : AppColors.textPrimary)
                .cornerRadius(10)
        }
    }

    private func save() {
        guard let sel = selectedIngredient else { return }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        var expiresStr: String?
        if let d = selectedExpiryDays, let expDate = Calendar.current.date(byAdding: .day, value: d, to: Date()) {
            expiresStr = formatter.string(from: expDate)
        }

        storage.addPantryLot(
            ingredientId: sel.id,
            ingredientName: sel.name,
            quantity: quantityText,
            unit: unit,
            expiresAt: expiresStr
        )
        dismiss()
    }
}

public struct PantryView: View {
    @State private var storage = AppStorage.shared
    @State private var showingAddSheet = false
    @State private var searchFilter = ""

    var filteredLots: [PantryLot] {
        if searchFilter.isEmpty { return storage.pantryLots }
        return storage.pantryLots.filter {
            CatalogueLoader.matches(text: $0.ingredientName, query: searchFilter)
        }
    }

    public var body: some View {
        NavigationStack {
            ZStack(alignment: .bottomTrailing) {
                if storage.pantryLots.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "refrigerator")
                            .font(.system(size: 64))
                            .foregroundColor(AppColors.primary.opacity(0.6))
                        Text("Tủ lạnh đang trống")
                            .font(.title3.bold())
                        Text("Bấm dấu cộng bên dưới để thêm nguyên liệu vào tủ nhanh chóng.")
                            .font(.subheadline)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 32)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        ForEach(filteredLots) { lot in
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(lot.ingredientName)
                                        .font(.headline)
                                    if let exp = lot.expiresAt {
                                        HStack(spacing: 6) {
                                            if let status = AppDateFormatter.formatExpiryStatus(exp) {
                                                Text("Hạn dùng: \(status.text)")
                                                    .font(.caption)
                                                    .foregroundColor(status.isWarning ? AppColors.danger : AppColors.textSecondary)
                                            } else {
                                                Text("Hạn dùng: \(AppDateFormatter.formatDateVN(exp))")
                                                    .font(.caption)
                                                    .foregroundColor(AppColors.textSecondary)
                                            }
                                            Button("+3 ngày") {
                                                storage.extendPantryLotExpiry(id: lot.id, daysToAdd: 3)
                                            }
                                            .font(.system(size: 11, weight: .bold))
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .frame(minWidth: 44, minHeight: 44)
                                            .background(AppColors.secondarySurface)
                                            .foregroundColor(AppColors.primary)
                                            .cornerRadius(6)
                                            .accessibilityLabel("Gia hạn thêm 3 ngày cho \(lot.ingredientName)")
                                        }
                                    }
                                }
                                Spacer()
                                Text("\(lot.remainingQuantity) \(lot.unit)")
                                    .font(.subheadline.bold())
                                    .foregroundColor(AppColors.primary)
                            }
                            .swipeActions(edge: .trailing) {
                                Button(role: .destructive) {
                                    storage.removePantryLot(id: lot.id)
                                } label: {
                                    Label("Xoá \(lot.ingredientName)", systemImage: "trash")
                                }
                            }
                        }
                    }
                    .searchable(text: $searchFilter, prompt: "Tìm trong tủ")
                }

                // Nút nổi thêm đồ nhanh
                Button {
                    showingAddSheet = true
                } label: {
                    Image(systemName: "plus")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                        .frame(width: 56, height: 56)
                        .background(AppColors.primary)
                        .clipShape(Circle())
                        .shadow(radius: 6)
                }
                .accessibilityLabel("Thêm thực phẩm vào tủ")
                .padding()
            }
            .navigationTitle("Tủ lạnh")
            .sheet(isPresented: $showingAddSheet) {
                AddPantrySheet()
                    .presentationDetents([.large])
            }
        }
    }

    private func isExpiringSoon(_ expDateStr: String) -> Bool {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        guard let exp = f.date(from: expDateStr) else { return false }
        let days = Calendar.current.dateComponents([.day], from: Date(), to: exp).day ?? 99
        return days <= 2
    }
}
