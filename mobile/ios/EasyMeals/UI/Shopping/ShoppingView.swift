import SwiftUI

public struct ShoppingView: View {
    @State private var storage = AppStorage.shared
    @State private var newItemName = ""
    @State private var newItemQty = "200"
    @State private var newItemUnit = "g"
    @State private var showingAddSheet = false

    var shareText: String {
        var lines = ["DANH SÁCH ĐI CHỢ - EASYMEALS"]
        for item in storage.shoppingItems {
            let mark = item.isBought ? "[x]" : "[ ]"
            lines.append("\(mark) \(item.ingredientName): \(item.neededQuantity) \(item.unit)")
        }
        return lines.joined(separator: "\n")
    }

    public var body: some View {
        NavigationStack {
            VStack {
                if storage.shoppingItems.isEmpty {
                    emptyShoppingView
                } else {
                    List {
                        ForEach(storage.shoppingItems) { item in
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

                                Text("\(item.neededQuantity) \(item.unit)")
                                    .font(.subheadline.bold())
                                    .foregroundColor(AppColors.primary)
                            }
                            .contentShape(Rectangle())
                            .onTapGesture {
                                storage.toggleShoppingItem(id: item.id)
                            }
                        }
                    }

                    // Thanh hành động dưới cùng
                    VStack(spacing: 12) {
                        let boughtCount = storage.shoppingItems.filter { $0.isBought }.count
                        if boughtCount > 0 {
                            Button {
                                storage.bulkAddBoughtToPantry()
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
                    }
                }
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showingAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddSheet) {
                addCustomItemSheet
                    .presentationDetents([.medium])
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
            .navigationTitle("Thêm món đi chợ")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Hủy") { showingAddSheet = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Thêm") {
                        storage.addCustomShoppingItem(name: newItemName, quantity: newItemQty, unit: newItemUnit)
                        newItemName = ""
                        showingAddSheet = false
                    }
                    .disabled(newItemName.isEmpty)
                }
            }
        }
    }
}
