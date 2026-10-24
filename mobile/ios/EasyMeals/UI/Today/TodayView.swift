import SwiftUI

public struct TodayView: View {
    @State private var storage = AppStorage.shared
    @State private var selectedMealPeriod = "lunch"
    @State private var showingErrorAlert = false
    @State private var errorMessage = ""

    var todayPlans: [MealPlan] {
        let todayStr = ISO8601DateFormatter().string(from: Date()).prefix(10).description
        return storage.mealPlans.filter { $0.plannedFor == todayStr }
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    if storage.mealPlans.isEmpty {
                        emptyPlanView
                    } else {
                        // Thẻ các bữa ăn hôm nay
                        ForEach(storage.mealPlans.prefix(4)) { plan in
                            mealPlanCard(plan: plan)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Hôm nay")
            .alert("Không đủ nguyên liệu", isPresented: $showingErrorAlert) {
                Button("Đã hiểu", role: .cancel) { }
            } message: {
                Text(errorMessage)
            }
        }
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

            Button {
                storage.generateNewPlan(days: 3)
            } label: {
                Label("Lên thực đơn 3 ngày ngay", systemImage: "sparkles")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(AppColors.primary)
                    .cornerRadius(14)
            }
            .padding(.horizontal)
        }
        .padding(.vertical, 40)
    }

    private func mealPlanCard(plan: MealPlan) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(periodTitle(plan.mealPeriod))
                        .font(.caption.bold())
                        .foregroundColor(AppColors.primary)
                    Text(plan.plannedFor)
                        .font(.headline)
                }
                Spacer()
                if plan.eatenAt != nil {
                    Label("Đã ăn", systemImage: "checkmark.circle.fill")
                        .font(.caption.bold())
                        .foregroundColor(.green)
                }
            }

            Divider()

            VStack(alignment: .leading, spacing: 10) {
                ForEach(plan.dishes) { dish in
                    HStack {
                        Image(systemName: categoryIcon(dish.category))
                            .foregroundColor(AppColors.primary)
                        Text(dish.recipeName)
                            .font(.body)
                        Spacer()
                        if dish.isLeftover {
                            Text("Ăn lại")
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.orange.opacity(0.15))
                                .foregroundColor(.orange)
                                .cornerRadius(6)
                        }
                    }
                }
            }

            Divider()

            if plan.eatenAt == nil {
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
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.impactOccurred()
        do {
            try storage.eatMeal(planId: planId)
        } catch let err as InsufficientStockError {
            self.errorMessage = err.message
            self.showingErrorAlert = true
        } catch {
            self.errorMessage = error.localizedDescription
            self.showingErrorAlert = true
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
