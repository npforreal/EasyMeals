import Foundation

/// F1 - Vòng 13: lịch sử & thống kê tính hoàn toàn trên thiết bị.
///
/// Quy ước schema (quyết định 2026-10-27): biến động kho chỉ thêm khoá ngoại tuỳ chọn
/// `ingredient_id`, `recipe_id`, `leftover_source_meal_id`; không lưu bản sao tên.
/// Không có API nào nhận dữ liệu lịch sử.
public struct HistoryMeal: Identifiable, Equatable, Sendable {
    public var id: String { planId }
    public let planId: String
    public let plannedFor: String
    public let mealPeriod: String
    public let eatenAt: String
    public let dishNames: [String]
    public let recipeIds: [String]
    public let servingsTotal: Int
    public let leftoverReuseCount: Int
}

public struct HistoryTopRecipe: Equatable, Sendable {
    public let recipeId: String
    public let name: String
    public let count: Int
}

public struct HistoryCooked: Equatable, Sendable {
    public let total: Int
    public let inWindow: Int
    public let lastEatenAt: String?
    public let meals: [HistoryMeal]
    public let topRecipes: [HistoryTopRecipe]
}

public struct HistoryStock: Equatable, Sendable {
    public let totalMovements: Int
    public let inWindow: Int
    public let consumedCount: Int
    public let restoredCount: Int
    public let byReason: [String: Int]
}

public struct HistoryLeftovers: Equatable, Sendable {
    public let reusedDishesInWindow: Int
    public let available: Bool
}

public struct HistoryExpiredLot: Equatable, Sendable {
    public let lotId: String
    public let ingredientId: String
    public let ingredientName: String
    public let remainingQuantity: String
    public let unit: String
    public let expiresAt: String
}

public struct HistoryWaste: Equatable, Sendable {
    public let tracked: Bool
    public let expiredLotCount: Int
    public let expiredLots: [HistoryExpiredLot]
}

public struct HistorySpending: Equatable, Sendable {
    public let currency: String
    public let total: Int
    public let inWindow: Int
    public let lotsWithPrice: Int
    public let lotsMissingPrice: Int
}

public struct HistorySummary: Equatable, Sendable {
    public let windowDays: Int
    public let from: String
    public let to: String
    public let cooked: HistoryCooked
    public let stock: HistoryStock
    public let leftovers: HistoryLeftovers
    public let waste: HistoryWaste
    public let spending: HistorySpending
}

public enum HistoryAggregator {

    private static func dayOnly(_ value: String?) -> String? {
        guard let value, value.count >= 10 else { return nil }
        let prefix = String(value.prefix(10))
        let parts = prefix.split(separator: "-")
        guard parts.count == 3 else { return nil }
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = "yyyy-MM-dd"
        guard formatter.date(from: prefix) != nil else { return nil }
        return prefix
    }

    private static func number(_ value: String?) -> Double {
        Double(value ?? "") ?? 0
    }

    /// Điền khoá ngoại cho movements cũ. Không ghi đè giá trị đã có, không xoá bản ghi.
    public static func backfillMovementIds(
        movements: [StockMovement],
        lots: [PantryLot],
        plans: [MealPlan]
    ) -> (movements: [StockMovement], changed: Bool) {
        let lotById = Dictionary(lots.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        let planById = Dictionary(plans.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        var changed = false

        let result = movements.map { movement -> StockMovement in
            var ingredientId = movement.ingredientId
            var recipeId = movement.recipeId

            if ingredientId?.isEmpty != false, let found = lotById[movement.pantryLotId]?.ingredientId, !found.isEmpty {
                ingredientId = found
                changed = true
            }
            if recipeId?.isEmpty != false, let planId = movement.mealPlanId, let plan = planById[planId] {
                let cooked = plan.dishes.filter { !$0.isLeftover }
                if cooked.count == 1, !cooked[0].recipeId.isEmpty {
                    recipeId = cooked[0].recipeId
                    changed = true
                }
            }

            if ingredientId == movement.ingredientId && recipeId == movement.recipeId {
                return movement
            }
            return StockMovement(
                id: movement.id,
                pantryLotId: movement.pantryLotId,
                quantityDelta: movement.quantityDelta,
                reason: movement.reason,
                mealPlanId: movement.mealPlanId,
                idempotencyKey: movement.idempotencyKey,
                createdAt: movement.createdAt,
                ingredientId: ingredientId,
                recipeId: recipeId,
                leftoverSourceMealId: movement.leftoverSourceMealId
            )
        }
        return (result, changed)
    }

    public static func build(
        plans: [MealPlan],
        movements: [StockMovement],
        pantryLots: [PantryLot],
        recipes: [Recipe] = [],
        now: String = String(ISO8601DateFormatter().string(from: Date()).prefix(10)),
        windowDays: Int = 30
    ) -> HistorySummary {
        let window = windowDays > 0 ? windowDays : 30
        let to = dayOnly(now) ?? String(ISO8601DateFormatter().string(from: Date()).prefix(10))

        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = "yyyy-MM-dd"
        let toDate = formatter.date(from: to) ?? Date()
        let fromDate = Calendar(identifier: .gregorian).date(byAdding: .day, value: -(window - 1), to: toDate) ?? toDate
        let from = formatter.string(from: fromDate)

        func inWindow(_ value: String?) -> Bool {
            guard let day = dayOnly(value) else { return false }
            return day >= from && day <= to
        }

        var recipeNames: [String: String] = [:]
        for recipe in recipes { recipeNames[recipe.id] = recipe.name.isEmpty ? recipe.id : recipe.name }
        for plan in plans {
            for dish in plan.dishes where recipeNames[dish.recipeId] == nil && !dish.recipeName.isEmpty {
                recipeNames[dish.recipeId] = dish.recipeName
            }
        }

        // ---- Bữa đã nấu ----
        let eatenPlans = plans
            .filter { !($0.eatenAt ?? "").isEmpty }
            .sorted { ($0.eatenAt ?? "") > ($1.eatenAt ?? "") }

        let meals: [HistoryMeal] = eatenPlans.map { plan in
            let cooked = plan.dishes.filter { !$0.isLeftover }
            return HistoryMeal(
                planId: plan.id,
                plannedFor: dayOnly(plan.plannedFor) ?? plan.plannedFor,
                mealPeriod: plan.mealPeriod,
                eatenAt: plan.eatenAt ?? "",
                dishNames: cooked.map { dish in
                    dish.recipeName.isEmpty ? (recipeNames[dish.recipeId] ?? dish.recipeId) : dish.recipeName
                },
                recipeIds: cooked.map(\.recipeId).filter { !$0.isEmpty },
                servingsTotal: cooked.reduce(0) { $0 + $1.servings },
                leftoverReuseCount: plan.dishes.filter(\.isLeftover).count
            )
        }

        let mealsInWindow = meals.filter { inWindow($0.eatenAt) }

        var counts: [String: Int] = [:]
        for meal in mealsInWindow { for id in meal.recipeIds { counts[id, default: 0] += 1 } }
        let topRecipes = counts
            .map { HistoryTopRecipe(recipeId: $0.key, name: recipeNames[$0.key] ?? $0.key, count: $0.value) }
            .sorted { $0.count != $1.count ? $0.count > $1.count : $0.name < $1.name }
            .prefix(5)
            .map { $0 }

        // ---- Biến động kho (đếm, không cộng trộn đơn vị) ----
        var byReason: [String: Int] = [:]
        var movementsInWindow = 0
        var consumed = 0
        var restored = 0
        for movement in movements {
            let reason = movement.reason.isEmpty ? "unknown" : movement.reason
            byReason[reason, default: 0] += 1
            guard inWindow(movement.createdAt) else { continue }
            movementsInWindow += 1
            let delta = number(movement.quantityDelta)
            if delta < 0 { consumed += 1 }
            if delta > 0 { restored += 1 }
        }

        // ---- Đồ dư & đồ quá hạn ----
        let leftoverReuse = mealsInWindow.reduce(0) { $0 + $1.leftoverReuseCount }
        let expired: [HistoryExpiredLot] = pantryLots.compactMap { lot in
            guard let expiry = dayOnly(lot.expiresAt), expiry < to, number(lot.remainingQuantity) > 0 else { return nil }
            return HistoryExpiredLot(
                lotId: lot.id,
                ingredientId: lot.ingredientId,
                ingredientName: lot.ingredientName,
                remainingQuantity: lot.remainingQuantity,
                unit: lot.unit,
                expiresAt: expiry
            )
        }.sorted { $0.expiresAt < $1.expiresAt }

        // ---- Chi tiêu đã nhập ----
        var total = 0
        var inWindowTotal = 0
        var withPrice = 0
        var missingPrice = 0
        for lot in pantryLots {
            if let price = Int(lot.price ?? ""), price >= 0 {
                withPrice += 1
                total += price
                if inWindow(lot.purchasedAt) { inWindowTotal += price }
            } else {
                missingPrice += 1
            }
        }

        return HistorySummary(
            windowDays: window,
            from: from,
            to: to,
            cooked: HistoryCooked(
                total: meals.count,
                inWindow: mealsInWindow.count,
                lastEatenAt: meals.first?.eatenAt,
                meals: meals,
                topRecipes: topRecipes
            ),
            stock: HistoryStock(
                totalMovements: movements.count,
                inWindow: movementsInWindow,
                consumedCount: consumed,
                restoredCount: restored,
                byReason: byReason
            ),
            leftovers: HistoryLeftovers(reusedDishesInWindow: leftoverReuse, available: !mealsInWindow.isEmpty),
            waste: HistoryWaste(tracked: false, expiredLotCount: expired.count, expiredLots: expired),
            spending: HistorySpending(
                currency: "VND",
                total: total,
                inWindow: inWindowTotal,
                lotsWithPrice: withPrice,
                lotsMissingPrice: missingPrice
            )
        )
    }
}
