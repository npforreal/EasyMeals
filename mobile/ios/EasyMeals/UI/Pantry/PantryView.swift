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
                                    Text(ing.category)
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

    private func select(ingredient: Ingredient) {
        self.selectedIngredient = ingredient
        self.unit = ingredient.defaultUnit
        self.searchText = ingredient.name
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
                                        Text("Hạn dùng: \(exp)")
                                            .font(.caption)
                                            .foregroundColor(isExpiringSoon(exp) ? AppColors.danger : AppColors.textSecondary)
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
                                    Label("Xoá", systemImage: "trash")
                                }
                            }
                        }
                    }
                    .searchable(text: $searchFilter, prompt: "Lọc đồ trong tủ...")
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
                .padding()
            }
            .navigationTitle("Tủ lạnh")
            .sheet(isPresented: $showingAddSheet) {
                AddPantrySheet()
                    .presentationDetents([.medium, .large])
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
