import SwiftUI

public struct TodayView: View {
    @State private var storage = AppStorage.shared
    @State private var selectedRecipe: Recipe?
    @State private var selectedServings: Int = 4
    @State private var showingDeficitConfirmation = false
    @State private var deficitPlanId: String?
    @State private var deficits: [DeficitItem] = []
    // Hộp thoại giữ/thay khi tạo thực đơn trùng ngày bữa chưa ăn (A2 - Vòng 13).
    @State private var showingPlanConflict = false
    @State private var planConflictDays = 3
    @AppStorage("selected_plan_days") private var selectedPlanDays: Int = PlanLimits.defaultDays
    @AppStorage("allow_leftovers") private var allowLeftovers: Bool = true
    @AppStorage("leftover_days") private var leftoverDays: Int = PlanLimits.leftoverDefaultDays

    var todayPlans: [MealPlan] {
        let todayStr = ISO8601DateFormatter().string(from: Date()).prefix(10).description
        return storage.mealPlans.filter { $0.plannedFor == todayStr }
    }

    var expiringFreshLots: [PantryLot] {
        guard let lastPlan = storage.mealPlans.max(by: { $0.plannedFor < $1.plannedFor }) else { return [] }
        return storage.pantryLots.filter { lot in
            guard let exp = lot.expiresAt else { return false }
            return exp <= lastPlan.plannedFor
        }
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    if storage.mealPlans.isEmpty {
                        emptyPlanView
                    } else {
                        if !expiringFreshLots.isEmpty {
                            freshnessAlertView
                        }
                        replanSectionView

                        ForEach(storage.mealPlans) { plan in
                            mealPlanCard(plan: plan)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Hôm nay")
            .sheet(item: $selectedRecipe) { recipe in
                NavigationStack {
                    RecipeDetailView(recipe: recipe, defaultServings: selectedServings)
                        .toolbar {
                            ToolbarItem(placement: .cancellationAction) {
                                Button("Đóng") { selectedRecipe = nil }
                            }
                        }
                }
            }
            .confirmationDialog("Không đủ nguyên liệu", isPresented: $showingDeficitConfirmation, titleVisibility: .visible) {
                Button("Thêm vào danh sách đi chợ") {
                    storage.addDeficitsToShoppingList(deficits: deficits)
                }
                Button("Vẫn đánh dấu đã ăn (trừ phần đang có)") {
                    if let planId = deficitPlanId {
                        try? storage.eatMeal(planId: planId, allowPartial: true)
                    }
                }
                Button("Huỷ", role: .cancel) { }
            } message: {
                let list = deficits.map { "• \($0.ingredientName): thiếu \($0.missingQuantity) \($0.unit)" }.joined(separator: "\n")
                Text("Bữa ăn còn thiếu các nguyên liệu sau trong kho:\n\(list)\n\nBạn muốn xử lý thế nào?")
            }
            .confirmationDialog(
                "Thực đơn mới trùng ngày",
                isPresented: $showingPlanConflict,
                titleVisibility: .visible
            ) {
                Button("Thay các bữa chưa ăn trong khoảng ngày này") {
                    storage.generateNewPlan(
                        days: planConflictDays,
                        mergeMode: "replace",
                        allowLeftovers: allowLeftovers,
                        leftoverDays: leftoverDays
                    )
                }
                Button("Giữ thực đơn cũ, chỉ thêm ngày chưa có") {
                    storage.generateNewPlan(
                        days: planConflictDays,
                        mergeMode: "keep",
                        allowLeftovers: allowLeftovers,
                        leftoverDays: leftoverDays
                    )
                }
                Button("Huỷ", role: .cancel) { }
            } message: {
                Text("Bạn muốn xử lý thế nào? Các bữa đã ăn luôn được giữ cùng lịch sử kho.")
            }
        }
    }

    /// A2: nếu đợt mới trùng bữa CHƯA ăn -> hỏi giữ/thay trước khi tạo; nút luôn dùng đường này.
    private func requestGeneratePlan(days: Int) {
        if storage.hasUneatenOverlap(days: days) {
            planConflictDays = days
            showingPlanConflict = true
        } else {
            storage.generateNewPlan(
                days: days,
                allowLeftovers: allowLeftovers,
                leftoverDays: leftoverDays
            )
        }
    }

    private var freshnessAlertView: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(AppColors.danger)
                .font(.title3)
            VStack(alignment: .leading, spacing: 2) {
                Text("Cảnh báo đồ tươi trong tủ")
                    .font(.subheadline.bold())
                    .foregroundColor(AppColors.danger)
                let names = expiringFreshLots.map { "\($0.ingredientName) (\(AppDateFormatter.formatDateVN($0.expiresAt!)))" }.joined(separator: ", ")
                Text("Nguyên liệu sắp hết hạn trong chu kỳ: \(names). Hãy ưu tiên nấu sớm hoặc gia hạn trong tủ lạnh.")
                    .font(.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            Spacer()
        }
        .padding()
        .background(AppColors.danger.opacity(0.1))
        .cornerRadius(12)
    }

    /// Tuỳ chọn đồ ăn dư (A1 - Vòng 13): bật/tắt dùng lại đồ dư và số ngày dùng lại (1-3, mặc định 2).
    private var leftoverOptionsView: some View {
        VStack(alignment: .leading, spacing: 8) {
            Toggle("Cho dùng lại đồ ăn dư", isOn: $allowLeftovers)
                .font(.subheadline)
            if allowLeftovers {
                HStack {
                    Text("Dùng lại trong tối đa:")
                        .font(.caption)
                        .foregroundColor(AppColors.textSecondary)
                    Picker("", selection: $leftoverDays) {
                        ForEach(PlanLimits.leftoverMinDays...PlanLimits.leftoverMaxDays, id: \.self) { d in
                            Text("\(d) ngày")
                        }
                    }
                    .pickerStyle(.segmented)
                    .fixedSize()
                }
            }
        }
    }

    private var replanSectionView: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Lên đợt thực đơn mới:")
                .font(.caption.bold())
                .foregroundColor(AppColors.textSecondary)
            HStack(spacing: 4) {
                ForEach(PlanLimits.minDays...PlanLimits.maxDays, id: \.self) { d in
                    Button {
                        selectedPlanDays = d
                    } label: {
                        Text("\(d)")
                            .font(.subheadline.bold())
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .background(selectedPlanDays == d ? AppColors.primary : AppColors.secondarySurface)
                            .foregroundColor(selectedPlanDays == d ? .white : AppColors.textPrimary)
                            .cornerRadius(8)
                    }
                }
            }
            leftoverOptionsView
            Button {
                requestGeneratePlan(days: selectedPlanDays)
            } label: {
                Label("Lên thực đơn \(selectedPlanDays) ngày", systemImage: "sparkles")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity, minHeight: 48)
                    .background(AppColors.primary)
                    .cornerRadius(12)
            }
        }
        .padding()
        .background(AppColors.secondarySurface.opacity(0.5))
        .cornerRadius(14)
    }

    private var emptyPlanView: some View {
        VStack(spacing: 20) {
            Image(systemName: "fork.knife.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(AppColors.primary)

            Text("Chưa có thực đơn")
                .font(.title2.bold())

            Text("Lập thực đơn thông minh dựa trên đồ có sẵn trong tủ, không trùng món và tái sử dụng thức ăn thừa.")
                .font(.subheadline)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            VStack(spacing: 8) {
                Text("Số ngày lập thực đơn (1–7 ngày):")
                    .font(.caption.bold())
                    .foregroundColor(AppColors.textSecondary)
                HStack(spacing: 4) {
                    ForEach(PlanLimits.minDays...PlanLimits.maxDays, id: \.self) { d in
                        Button {
                            selectedPlanDays = d
                        } label: {
                            Text("\(d)")
                                .font(.subheadline.bold())
                                .frame(maxWidth: .infinity, minHeight: 48)
                                .background(selectedPlanDays == d ? AppColors.primary : AppColors.secondarySurface)
                                .foregroundColor(selectedPlanDays == d ? .white : AppColors.textPrimary)
                                .cornerRadius(10)
                        }
                    }
                }
            }
            .padding(.top, 8)

            leftoverOptionsView

            Button {
                requestGeneratePlan(days: selectedPlanDays)
            } label: {
                Label("Lên thực đơn \(selectedPlanDays) ngày", systemImage: "sparkles")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity, minHeight: 48)
                    .background(AppColors.primary)
                    .cornerRadius(14)
            }
            .padding(.horizontal)
        }
        .padding(.vertical, 30)
    }

    private func mealPlanCard(plan: MealPlan) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    let periodLabel = GeneratedTokens.Labels.meal_periods[plan.mealPeriod]?.uppercased() ?? periodTitle(plan.mealPeriod)
                    Text(periodLabel)
                        .font(.caption.bold())
                        .foregroundColor(AppColors.primary)
                    Text(AppDateFormatter.formatRelativeDate(plan.plannedFor))
                        .font(.headline)
                }
                Spacer()
                if plan.eatenAt != nil {
                    Label("Đã ăn", systemImage: "checkmark.circle.fill")
                        .font(.caption.bold())
                        .foregroundColor(AppColors.primary)
                }
            }

            Divider()

            VStack(alignment: .leading, spacing: 10) {
                ForEach(plan.dishes) { dish in
                    HStack(spacing: 8) {
                        Image(systemName: categoryIcon(dish.category))
                            .foregroundColor(AppColors.primary)
                        Text(dish.recipeName)
                            .font(.body)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                        Spacer(minLength: 4)
                        if dish.isLeftover {
                            Text("Ăn lại")
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(AppColors.warning.opacity(0.15))
                                .foregroundColor(AppColors.warning)
                                .cornerRadius(6)
                        }
                        Button {
                            if let recipe = storage.recipes.first(where: { $0.id == dish.recipeId }) {
                                selectedRecipe = recipe
                                selectedServings = dish.servings
                            }
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "book.pages")
                                Text("Xem công thức")
                            }
                            .font(.caption)
                            .foregroundColor(AppColors.primary)
                        }
                        .buttonStyle(.borderless)
                    }
                }
            }

            Divider()

            if plan.eatenAt == nil {
                VStack(spacing: 8) {
                    Button {
                        handleEatMeal(planId: plan.id)
                    } label: {
                        HStack {
                            Image(systemName: "checkmark")
                            Text("Đã ăn (Trừ kho)")
                        }
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(AppColors.primary)
                        .cornerRadius(12)
                    }

                    Button {
                        try? storage.regenerateMeal(planId: plan.id)
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "arrow.triangle.2.circlepath")
                            Text("Sinh lại bữa này (Đổi món)")
                        }
                        .font(.subheadline)
                        .foregroundColor(AppColors.primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(AppColors.secondarySurface)
                        .cornerRadius(10)
                    }
                }
            } else {
                Button {
                    storage.undoLastEatMeal()
                } label: {
                    Text("Hoàn tác bữa ăn này")
                        .font(.subheadline.bold())
                        .foregroundColor(AppColors.primary)
                        .frame(maxWidth: .infinity)
                }
            }
        }
        .cardStyle()
    }

    private func handleEatMeal(planId: String) {
        let (canEat, missing) = storage.checkMealStock(planId: planId)
        if canEat {
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()
            try? storage.eatMeal(planId: planId, allowPartial: false)
        } else {
            deficitPlanId = planId
            deficits = Array(missing.values)
            showingDeficitConfirmation = true
        }
    }

    private func periodTitle(_ p: String) -> String {
        switch p {
        case "lunch": return "BỮA TRƯA"
        case "dinner": return "BỮA TỐI"
        default: return "BỮA ĂN"
        }
    }

    private func categoryIcon(_ c: String) -> String {
        switch c {
        case "man": return "flame.fill"
        case "rau": return "leaf.fill"
        case "canh": return "drop.fill"
        default: return "circle"
        }
    }
}
