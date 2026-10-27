import SwiftUI

public struct ShoppingView: View {
    @State private var storage = AppStorage.shared
    @State private var newItemName = ""
    @State private var newItemQty = "200"
    @State private var newItemUnit = "g"
    @State private var newItemCategory = "khac"
    @State private var newItemPrice = ""
    @State private var showingAddSheet = false
    @State private var editingPriceItem: ShoppingItem? = nil
    @State private var editingPriceValue = ""
    // A4 - Vòng 13: hộp thoại xác nhận mua vào tủ (lượng thực mua + hạn dùng).
    @State private var showingPurchaseSheet = false
    @State private var purchaseQuantities: [String: String] = [:]
    @State private var purchaseExpiries: [String: Date] = [:]

    private let categoryLabels: [String: String] = [
        "thit": "Thịt tươi sống",
        "gia_cam": "Gia cầm & trứng",
        "hai_san": "Hải sản tươi sống",
        "trung_sua": "Trứng & Sữa",
        "rau_cu": "Rau tươi & nấm",
        "cu_qua": "Củ & quả",
        "gao_bot_mi": "Gạo, mì & bột",
        "gia_vi": "Gia vị & phụ liệu",
        "nuoc_cham_dau": "Nước chấm & dầu ăn",
        "khac": "Mặt hàng khác"
    ]

    private let categoriesOrder: [String] = [
        "thit", "gia_cam", "hai_san", "trung_sua", "rau_cu",
        "cu_qua", "gao_bot_mi", "gia_vi", "nuoc_cham_dau", "khac"
    ]

    private func formatVnd(_ amountStr: String) -> String {
        let val = Double(amountStr) ?? 0
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.locale = Locale(identifier: "vi_VN")
        let formatted = formatter.string(from: NSNumber(value: Int(val))) ?? "0"
        return "\(formatted) đ"
    }

    var budget: EasyMealsEngine.ShoppingBudgetResult {
        EasyMealsEngine.calculateShoppingBudget(storage.shoppingItems)
    }

    var groupedItems: [String: [ShoppingItem]] {
        EasyMealsEngine.groupShoppingItemsByCategory(storage.shoppingItems)
    }

    var shareText: String {
        var lines = ["DANH SÁCH ĐI CHỢ - EASYMEALS\n"]
        for cat in categoriesOrder {
            guard let items = groupedItems[cat], !items.isEmpty else { continue }
            lines.append("=== \(categoryLabels[cat] ?? "Mặt hàng khác") ===")
            for item in items {
                let mark = item.isBought ? "[x]" : "[ ]"
                let priceText = (item.price?.isEmpty == false) ? " (~\(formatVnd(item.price!)))" : ""
                lines.append("\(mark) \(item.ingredientName): \(item.neededQuantity) \(item.unit)\(priceText)")
            }
            lines.append("")
        }
        if budget.itemsWithPriceCount > 0 {
            lines.append("Dự toán: \(formatVnd(budget.totalEstimatedBudget)) | Đã chi: \(formatVnd(budget.totalSpent))")
        }
        return lines.joined(separator: "\n")
    }

    public var body: some View {
        NavigationStack {
            VStack {
                if storage.shoppingItems.isEmpty {
                    emptyShoppingView
                } else {
                    // Thẻ Ngân Sách & Chi tiêu (B4)
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Ngân sách & Chi tiêu")
                                .font(.subheadline.bold())
                                .foregroundColor(AppColors.primary)
                            Spacer()
                            Text("\(budget.itemsWithPriceCount)/\(budget.totalItemsCount) món có giá")
                                .font(.caption)
                                .foregroundColor(AppColors.textSecondary)
                        }
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Dự toán tổng")
                                    .font(.caption2)
                                    .foregroundColor(AppColors.textSecondary)
                                Text(formatVnd(budget.totalEstimatedBudget))
                                    .font(.subheadline.bold())
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text("Đã chi")
                                    .font(.caption2)
                                    .foregroundColor(AppColors.textSecondary)
                                Text(formatVnd(budget.totalSpent))
                                    .font(.subheadline.bold())
                                    .foregroundColor(AppColors.primary)
                            }
                        }
                    }
                    .padding(12)
                    .background(AppColors.primary.opacity(0.08))
                    .cornerRadius(12)
                    .padding(.horizontal)
                    .padding(.top, 4)

                    List {
                        ForEach(categoriesOrder, id: \.self) { cat in
                            if let items = groupedItems[cat], !items.isEmpty {
                                Section(header: Text(categoryLabels[cat] ?? "Mặt hàng khác").font(.caption.bold())) {
                                    ForEach(items) { item in
                                        HStack {
                                            Image(systemName: item.isBought ? "checkmark.circle.fill" : "circle")
                                                .foregroundColor(item.isBought ? AppColors.primary : AppColors.textSecondary)
                                                .font(.title3)

                                            VStack(alignment: .leading, spacing: 2) {
                                                Text(item.ingredientName)
                                                    .font(.body)
                                                    .strikethrough(item.isBought, color: .secondary)
                                                    .foregroundColor(item.isBought ? .secondary : AppColors.textPrimary)

                                                if !item.dishNames.isEmpty {
                                                    Text("Cho món: \(item.dishNames.joined(separator: ", "))")
                                                        .font(.caption2)
                                                        .foregroundColor(.secondary)
                                                }
                                            }

                                            Spacer()

                                            VStack(alignment: .trailing, spacing: 2) {
                                                Text("\(item.neededQuantity) \(item.unit)")
                                                    .font(.subheadline.bold())
                                                    .foregroundColor(AppColors.primary)

                                                Button {
                                                    editingPriceItem = item
                                                    editingPriceValue = item.price ?? ""
                                                } label: {
                                                    if let p = item.price, !p.isEmpty {
                                                        Text(formatVnd(p))
                                                            .font(.caption2)
                                                            .foregroundColor(AppColors.textPrimary)
                                                    } else {
                                                        Text("+ Giá")
                                                            .font(.caption2)
                                                            .foregroundColor(AppColors.primary)
                                                    }
                                                }
                                                .buttonStyle(.plain)
                                            }

                                            Button {
                                                storage.deleteShoppingItem(id: item.id)
                                            } label: {
                                                Image(systemName: "trash")
                                                    .font(.caption)
                                                    .foregroundColor(AppColors.textSecondary.opacity(0.6))
                                                    .frame(width: 44, height: 44)
                                            }
                                            .buttonStyle(.plain)
                                            .accessibilityLabel("Xoá \(item.ingredientName) khỏi danh sách đi chợ")
                                            .padding(.leading, 6)
                                        }
                                        .contentShape(Rectangle())
                                        .onTapGesture {
                                            storage.toggleShoppingItem(id: item.id)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)

                    // Thanh hành động dưới cùng
                    VStack(spacing: 12) {
                        let boughtCount = storage.shoppingItems.filter { $0.isBought }.count
                        if boughtCount > 0 {
                            Button {
                                showingPurchaseSheet = true
                            } label: {
                                Label("Cho \(boughtCount) món đã mua vào tủ lạnh", systemImage: "refrigerator")
                                    .font(.headline)
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(AppColors.primary)
                                    .cornerRadius(14)
                            }
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Đi chợ")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if !storage.shoppingItems.isEmpty {
                        ShareLink(item: shareText) {
                            Image(systemName: "square.and.arrow.up")
                        }
                        .accessibilityLabel("Chia sẻ danh sách đi chợ")
                    }
                }
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showingAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityLabel("Thêm mục cần mua ngoài kế hoạch")
                }
            }
            .sheet(isPresented: $showingAddSheet) {
                addCustomItemSheet
                    .presentationDetents([.medium, .large])
            }
            .alert("Nhập giá thực tế", isPresented: Binding(
                get: { editingPriceItem != nil },
                set: { if !$0 { editingPriceItem = nil } }
            )) {
                TextField("Đơn giá VNĐ", text: $editingPriceValue)
                    .keyboardType(.numberPad)
                Button("Lưu giá") {
                    if let item = editingPriceItem {
                        storage.updateShoppingItemPrice(id: item.id, price: editingPriceValue)
                    }
                    editingPriceItem = nil
                }
                Button("Huỷ", role: .cancel) {
                    editingPriceItem = nil
                }
            } message: {
                if let item = editingPriceItem {
                    Text("Nhập giá bạn thực tế chi trả cho \(item.ingredientName):")
                }
            }
            // A4 - Vòng 13: xác nhận mua vào tủ — chỉnh lượng thực mua & hạn dùng từng món.
            .sheet(isPresented: $showingPurchaseSheet) {
                purchaseConfirmSheet
            }
        }
    }

    private var emptyShoppingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "cart")
                .font(.system(size: 64))
                .foregroundColor(AppColors.primary.opacity(0.6))
            Text("Danh sách đi chợ trống")
                .font(.title3.bold())
            Text("Khi lên thực đơn, các nguyên liệu còn thiếu trong tủ sẽ tự động xuất hiện ở đây.")
                .font(.subheadline)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button {
                showingAddSheet = true
            } label: {
                Label("Thêm món cần mua", systemImage: "plus")
                    .font(.subheadline.bold())
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(AppColors.secondarySurface)
                    .cornerRadius(10)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var addCustomItemSheet: some View {
        NavigationStack {
            Form {
                Section(header: Text("Thông tin nguyên liệu")) {
                    TextField("Tên món cần mua", text: $newItemName)
                    HStack {
                        TextField("Số lượng", text: $newItemQty)
                            .keyboardType(.decimalPad)
                        Picker("Đơn vị", selection: $newItemUnit) {
                            Text("g").tag("g")
                            Text("kg").tag("kg")
                            Text("ml").tag("ml")
                            Text("l").tag("l")
                            Text("piece").tag("piece")
                        }
                    }
                }
                Section(header: Text("Quầy hàng & Giá")) {
                    Picker("Quầy hàng", selection: $newItemCategory) {
                        ForEach(categoriesOrder, id: \.self) { cat in
                            Text(categoryLabels[cat] ?? cat).tag(cat)
                        }
                    }
                    TextField("Đơn giá VNĐ (tuỳ chọn)", text: $newItemPrice)
                        .keyboardType(.numberPad)
                }
            }
            .navigationTitle("Thêm món đi chợ")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Hủy") { showingAddSheet = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Thêm") {
                        storage.addCustomShoppingItem(
                            name: newItemName,
                            quantity: newItemQty,
                            unit: newItemUnit,
                            category: newItemCategory,
                            price: newItemPrice
                        )
                        newItemName = ""
                        newItemPrice = ""
                        showingAddSheet = false
                    }
                    .disabled(newItemName.isEmpty)
                }
            }
        }
    }

    /// A4 - Vòng 13: sheet xác nhận mua vào tủ — cho phép nhập LƯỢNG THỰC MUA khác
    /// ước tính và HẠN DÙNG (mặc định theo nhóm nguyên liệu) cho từng món đã tích chọn.
    private var purchaseConfirmSheet: some View {
        let boughtItems = storage.shoppingItems.filter { $0.isBought }
        return NavigationStack {
            Form {
                if boughtItems.isEmpty {
                    Text("Chưa chọn món nào đã mua.")
                }
                ForEach(boughtItems) { item in
                    VStack(alignment: .leading, spacing: 8) {
                        Text("\(item.ingredientName): ước tính \(item.neededQuantity) \(item.unit)")
                            .font(.subheadline.bold())
                        TextField("Thực mua (\(item.unit))", text: bindingOrCompute(purchaseQuantities, key: item.id, default: item.neededQuantity))
                            .keyboardType(.decimalPad)
                        DatePicker(
                            "Hạn dùng",
                            selection: bindingOrComputeDate(
                                purchaseExpiries,
                                key: item.id,
                                default: defaultDate(for: item)
                            ),
                            displayedComponents: .date
                        )
                    }
                }
            }
            .navigationTitle("Xác nhận mua vào tủ")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Huỷ") { showingPurchaseSheet = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Cho \(boughtItems.count) món vào tủ lạnh") {
                        let overrides = boughtItems.map { item -> PurchaseOverride in
                            let qty = purchaseQuantities[item.id] ?? item.neededQuantity
                            let expDate = purchaseExpiries[item.id] ?? defaultDate(for: item)
                            let formatter = ISO8601DateFormatter()
                            formatter.formatOptions = [.withFullDate]
                            return PurchaseOverride(
                                itemId: item.id,
                                actualQuantity: qty,
                                expiresAt: formatter.string(from: expDate)
                            )
                        }
                        storage.bulkAddBoughtToPantry(overrides: overrides)
                        purchaseQuantities = [:]
                        purchaseExpiries = [:]
                        showingPurchaseSheet = false
                    }
                    .disabled(boughtItems.isEmpty)
                }
            }
        }
    }

    private func defaultDate(for item: ShoppingItem) -> Date {
        let category = storage.categoryOf(ingredientId: item.ingredientId)
        let named = ShoppingDefaults.expiryDate(category: category)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        formatter.timeZone = .current
        return formatter.date(from: named) ?? Date()
    }

    private func bindingOrCompute(
        _ dict: [String: String],
        key: String,
        default defaultValue: String
    ) -> Binding<String> {
        Binding(
            get: { dict[key] ?? defaultValue },
            set: { purchaseQuantities[key] = $0 }
        )
    }

    private func bindingOrComputeDate(
        _ dict: [String: Date],
        key: String,
        default defaultValue: Date
    ) -> Binding<Date> {
        Binding(
            get: { dict[key] ?? defaultValue },
            set: { purchaseExpiries[key] = $0 }
        )
    }
}
