import SwiftUI

/// Chọn món thủ công cho một bữa chưa ăn: thêm món mới hoặc đổi một món (D2b).
/// Món chứa nguyên liệu người dùng đã đặt cần tránh chỉ được thêm sau khi xác nhận.
struct RecipePickerSheet: View {
    enum Mode: Equatable {
        case add
        case swap(oldDishId: String, category: String)
    }

    let mealPlanId: String
    let mode: Mode
    let onDone: () -> Void

    @State private var storage = AppStorage.shared
    @SwiftUI.AppStorage("easymeals.recipe.avoidedIngredientIds") private var avoidedIngredientIDs = ""
    @State private var query = ""
    @State private var pendingViolation: (recipe: Recipe, ingredientName: String)?
    @State private var errorMessage: String?
    @Environment(\.dismiss) private var dismiss

    private var avoidedIDs: Set<String> { Set(avoidedIngredientIDs.split(separator: ",").map(String.init)) }

    private var candidates: [Recipe] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return storage.recipes.filter { recipe in
            if case .swap(_, let category) = mode, recipe.category != category { return false }
            return q.isEmpty || recipe.name.lowercased().contains(q)
        }
    }

    private func violation(of recipe: Recipe) -> String? {
        guard let hit = recipe.ingredients.first(where: { avoidedIDs.contains($0.ingredientId) }) else { return nil }
        return storage.ingredients.first(where: { $0.id == hit.ingredientId })?.name ?? "nguyên liệu đã chọn"
    }

    private func apply(_ recipe: Recipe, confirmed: Bool) {
        do {
            switch mode {
            case .add:
                try storage.addDish(mealPlanId: mealPlanId, recipeId: recipe.id, confirmedAvoidance: confirmed)
            case .swap(let oldDishId, _):
                try storage.swapDish(mealPlanId: mealPlanId, oldDishId: oldDishId, newRecipeId: recipe.id, confirmedAvoidance: confirmed)
            }
            onDone()
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func choose(_ recipe: Recipe) {
        if let name = violation(of: recipe) {
            pendingViolation = (recipe, name)
        } else {
            apply(recipe, confirmed: false)
        }
    }

    var body: some View {
        NavigationStack {
            List(candidates) { recipe in
                Button { choose(recipe) } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(recipe.name).foregroundColor(AppColors.textPrimary)
                            if violation(of: recipe) != nil {
                                Text("Chứa nguyên liệu bạn cần tránh")
                                    .font(.caption)
                                    .foregroundColor(AppColors.warning)
                            }
                        }
                        Spacer()
                    }
                }
                .accessibilityIdentifier("recipe-picker-\(recipe.id)")
            }
            .searchable(text: $query, prompt: "Tìm tên món")
            .navigationTitle(mode == .add ? "Thêm món" : "Đổi món")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Huỷ") { dismiss() } }
            }
            .alert(
                "Món này cần tránh",
                isPresented: Binding(get: { pendingViolation != nil }, set: { if !$0 { pendingViolation = nil } })
            ) {
                Button("Huỷ", role: .cancel) { pendingViolation = nil }
                Button("Vẫn thêm") {
                    if let pending = pendingViolation { apply(pending.recipe, confirmed: true) }
                    pendingViolation = nil
                }
            } message: {
                Text("Món này chứa \(pendingViolation?.ingredientName ?? "nguyên liệu đã chọn") mà bạn đã đặt cần tránh. Vẫn thêm?")
            }
            .alert("Không thực hiện được", isPresented: Binding(get: { errorMessage != nil }, set: { if !$0 { errorMessage = nil } })) {
                Button("Đóng", role: .cancel) { errorMessage = nil }
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }
}
