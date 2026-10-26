import Foundation

public struct IncompatibleUnitError: Error, LocalizedError, Equatable {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}

public struct InsufficientStockError: Error, LocalizedError, Equatable {
    public let message: String
    public let deficits: [String: DeficitItem]
    public init(_ message: String, deficits: [String: DeficitItem] = [:]) {
        self.message = message
        self.deficits = deficits
    }
    public var errorDescription: String? { message }
}

public struct MealPlanError: Error, LocalizedError, Equatable {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}

public enum UnitDimensions {
    private static let dimensions: [String: UnitDimension] = [
        "g": .mass,
        "kg": .mass,
        "ml": .volume,
        "l": .volume,
        "piece": .count
    ]

    private static let multipliers: [String: ExactDecimal] = [
        "g": ExactDecimal("1"),
        "kg": ExactDecimal("1000"),
        "ml": ExactDecimal("1"),
        "l": ExactDecimal("1000"),
        "piece": ExactDecimal("1")
    ]

    public static func dimension(of unit: String) -> UnitDimension? {
        dimensions[unit]
    }

    public static func areCompatible(_ a: String, _ b: String) -> Bool {
        guard let da = dimension(of: a), let db = dimension(of: b) else { return false }
        return da == db
    }

    public static func convert(quantity: ExactDecimal, from fromUnit: String, to toUnit: String) throws -> ExactDecimal {
        if fromUnit == toUnit { return quantity }
        guard let dimFrom = dimension(of: fromUnit),
              let dimTo = dimension(of: toUnit),
              dimFrom == dimTo else {
            throw IncompatibleUnitError(
                "Không thể chuyển đổi đơn vị '\(fromUnit)' sang '\(toUnit)' vì khác thứ nguyên."
            )
        }
        guard let multFrom = multipliers[fromUnit], let multTo = multipliers[toUnit] else {
            throw IncompatibleUnitError("Không có hệ số quy đổi cho '\(fromUnit)' hoặc '\(toUnit)'.")
        }

        let base = quantity * multFrom
        return base / multTo
    }
}

public struct AggregatedRequirement: Equatable {
    public let ingredientId: String
    public let name: String
    public var quantity: ExactDecimal
    public let unit: String
}

public enum EasyMealsEngine {

    public static func aggregateRequirements(recipe: Recipe, multiplier: String = "1") -> [AggregatedRequirement] {
        let mult = ExactDecimal(multiplier)
        var merged: [String: AggregatedRequirement] = [:]
        var mergedKeys: [String] = []

        for req in recipe.ingredients {
            let qty = ExactDecimal(req.quantity) * mult
            let dimStr = UnitDimensions.dimension(of: req.unit)?.rawValue ?? "unknown"
            let key = "\(req.ingredientId)|\(dimStr)"

            if var existing = merged[key] {
                let converted = try? UnitDimensions.convert(quantity: qty, from: req.unit, to: existing.unit)
                existing.quantity = existing.quantity + (converted ?? qty)
                merged[key] = existing
            } else {
                mergedKeys.append(key)
                merged[key] = AggregatedRequirement(
                    ingredientId: req.ingredientId,
                    name: req.ingredientName,
                    quantity: qty,
                    unit: req.unit
                )
            }
        }
        return mergedKeys.compactMap { merged[$0] }
    }

    public static func lotSortKey(for lot: PantryLot) -> String {
        let exp = lot.expiresAt ?? "9999-12-31"
        let pur = lot.purchasedAt ?? "1970-01-01"
        return "\(exp)_\(pur)"
    }

    public static func findConversionsForTarget(
        ingredientId: String,
        conversions: [Conversion]?
    ) -> [Conversion] {
        guard let conversions = conversions else { return [] }
        return conversions.filter {
            $0.toIngredientId == ingredientId && ExactDecimal($0.ratio) > .zero
        }
    }

    public static func getTotalIngredientStock(
        pantryLots: [PantryLot],
        ingredientId: String,
        targetUnit: String,
        conversions: [Conversion]? = nil
    ) -> ExactDecimal {
        var total = ExactDecimal.zero
        for lot in pantryLots {
            if lot.ingredientId != ingredientId || !UnitDimensions.areCompatible(lot.unit, targetUnit) {
                continue
            }
            let rem = ExactDecimal(lot.remainingQuantity)
            if rem > .zero {
                if let converted = try? UnitDimensions.convert(quantity: rem, from: lot.unit, to: targetUnit) {
                    total = total + converted
                }
            }
        }

        let targetConvs = findConversionsForTarget(ingredientId: ingredientId, conversions: conversions)
        for conv in targetConvs {
            if !UnitDimensions.areCompatible(conv.toUnit, targetUnit) { continue }
            let ratio = ExactDecimal(conv.ratio)
            for lot in pantryLots {
                if lot.ingredientId == conv.fromIngredientId && UnitDimensions.areCompatible(lot.unit, conv.fromUnit) {
                    let rem = ExactDecimal(lot.remainingQuantity)
                    if rem > .zero {
                        guard let rawInFromUnit = try? UnitDimensions.convert(quantity: rem, from: lot.unit, to: conv.fromUnit) else { continue }
                        let prodInToUnit = rawInFromUnit * ratio
                        guard let converted = try? UnitDimensions.convert(quantity: prodInToUnit, from: conv.toUnit, to: targetUnit) else { continue }
                        total = total + converted
                    }
                }
            }
        }
        return total
    }

    public static func consumeAvailable(
        pantryLots: inout [PantryLot],
        ingredientId: String,
        quantity: ExactDecimal,
        unit: String,
        conversions: [Conversion]? = nil
    ) -> ExactDecimal {
        var needed = quantity
        var consumed = ExactDecimal.zero

        pantryLots.sort { lotSortKey(for: $0) < lotSortKey(for: $1) }

        // 1. Trừ lô trực tiếp
        for i in 0..<pantryLots.count {
            if needed <= .zero { break }
            if pantryLots[i].ingredientId != ingredientId || !UnitDimensions.areCompatible(pantryLots[i].unit, unit) {
                continue
            }
            let rem = ExactDecimal(pantryLots[i].remainingQuantity)
            if rem <= .zero { continue }

            guard let available = try? UnitDimensions.convert(quantity: rem, from: pantryLots[i].unit, to: unit) else {
                continue
            }

            let take = available < needed ? available : needed
            let takeInLotUnit = (take == available)
                ? rem
                : (try? UnitDimensions.convert(quantity: take, from: unit, to: pantryLots[i].unit)) ?? rem

            pantryLots[i].remainingQuantity = (rem - takeInLotUnit).description
            needed = needed - take
            consumed = consumed + take
        }

        // 2. Trừ qua quy đổi (FIFO)
        if needed > .zero {
            let targetConvs = findConversionsForTarget(ingredientId: ingredientId, conversions: conversions)
            for conv in targetConvs {
                if needed <= .zero { break }
                if !UnitDimensions.areCompatible(conv.toUnit, unit) { continue }
                let ratio = ExactDecimal(conv.ratio)

                for i in 0..<pantryLots.count {
                    if needed <= .zero { break }
                    if pantryLots[i].ingredientId != conv.fromIngredientId || !UnitDimensions.areCompatible(pantryLots[i].unit, conv.fromUnit) {
                        continue
                    }
                    let rem = ExactDecimal(pantryLots[i].remainingQuantity)
                    if rem <= .zero { continue }

                    guard let neededInToUnit = try? UnitDimensions.convert(quantity: needed, from: unit, to: conv.toUnit) else { continue }
                    let neededRawInFromUnit = neededInToUnit / ratio
                    guard let rawAvailable = try? UnitDimensions.convert(quantity: rem, from: pantryLots[i].unit, to: conv.fromUnit) else { continue }

                    let takeRaw = rawAvailable < neededRawInFromUnit ? rawAvailable : neededRawInFromUnit
                    let takeInLotUnit = (takeRaw == rawAvailable)
                        ? rem
                        : (try? UnitDimensions.convert(quantity: takeRaw, from: conv.fromUnit, to: pantryLots[i].unit)) ?? rem

                    pantryLots[i].remainingQuantity = (rem - takeInLotUnit).description
                    let yieldedInToUnit = takeRaw * ratio
                    guard let yieldedUnit = try? UnitDimensions.convert(quantity: yieldedInToUnit, from: conv.toUnit, to: unit) else { continue }
                    needed = needed - yieldedUnit
                    consumed = consumed + yieldedUnit
                }
            }
        }

        return consumed
    }

    public static func checkRecipeStock(
        recipe: Recipe,
        pantryLots: [PantryLot],
        multiplier: String = "1",
        conversions: [Conversion]? = nil
    ) -> (canCook: Bool, deficits: [String: DeficitItem]) {
        var deficits: [String: DeficitItem] = [:]
        let requirements = aggregateRequirements(recipe: recipe, multiplier: multiplier)

        for req in requirements {
            let available = getTotalIngredientStock(pantryLots: pantryLots, ingredientId: req.ingredientId, targetUnit: req.unit, conversions: conversions)
            if available < req.quantity {
                let missing = req.quantity - available
                deficits[req.ingredientId] = DeficitItem(
                    ingredientName: req.name,
                    missingQuantity: missing.description,
                    unit: req.unit
                )
            }
        }

        return (deficits.isEmpty, deficits)
    }

    public struct StockDeductionOutcome: Equatable {
        public let updatedLots: [PantryLot]
        public let movements: [StockMovement]
        public let deficits: [String: DeficitItem]

        public init(updatedLots: [PantryLot], movements: [StockMovement], deficits: [String: DeficitItem]) {
            self.updatedLots = updatedLots
            self.movements = movements
            self.deficits = deficits
        }
    }

    public static func executeStockDeduction(
        pantryLots: [PantryLot],
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: [Conversion]? = nil,
        allowPartial: Bool = false
    ) throws -> StockDeductionOutcome {
        if !allowPartial {
            let (canCook, deficits) = checkRecipeStock(recipe: recipe, pantryLots: pantryLots, multiplier: multiplier, conversions: conversions)
            if !canCook {
                throw InsufficientStockError("Không đủ nguyên liệu để nấu món '\(recipe.name)'", deficits: deficits)
            }
        }

        let requirements = aggregateRequirements(recipe: recipe, multiplier: multiplier)
        var clonedLots = pantryLots
        var updatedLotsMap: [String: PantryLot] = [:]
        var updatedLotKeys: [String] = []
        var movements: [StockMovement] = []
        var deficits: [String: DeficitItem] = [:]

        for req in requirements {
            var remainingNeeded = req.quantity

            // 1. Trừ các lô trực tiếp
            var directIndices = clonedLots.indices.filter {
                clonedLots[$0].ingredientId == req.ingredientId &&
                UnitDimensions.areCompatible(clonedLots[$0].unit, req.unit) &&
                ExactDecimal(clonedLots[$0].remainingQuantity) > .zero
            }
            directIndices.sort { lotSortKey(for: clonedLots[$0]) < lotSortKey(for: clonedLots[$1]) }

            for idx in directIndices {
                if remainingNeeded <= .zero { break }
                let lot = clonedLots[idx]
                let lotRem = ExactDecimal(lot.remainingQuantity)

                guard let availableInReq = try? UnitDimensions.convert(quantity: lotRem, from: lot.unit, to: req.unit) else {
                    continue
                }

                let deductedLotUnit: ExactDecimal
                if availableInReq <= remainingNeeded {
                    deductedLotUnit = lotRem
                    clonedLots[idx].remainingQuantity = "0"
                    remainingNeeded = remainingNeeded - availableInReq
                } else {
                    let deductedReqUnit = remainingNeeded
                    deductedLotUnit = (try? UnitDimensions.convert(quantity: deductedReqUnit, from: req.unit, to: lot.unit)) ?? lotRem
                    clonedLots[idx].remainingQuantity = (lotRem - deductedLotUnit).description
                    remainingNeeded = .zero
                }

                if updatedLotsMap[lot.id] == nil {
                    updatedLotKeys.append(lot.id)
                }
                updatedLotsMap[lot.id] = clonedLots[idx]
                let mov = StockMovement(
                    id: UUID().uuidString,
                    pantryLotId: lot.id,
                    quantityDelta: "-\(deductedLotUnit.description)",
                    reason: "meal_consumption",
                    mealPlanId: mealPlanId,
                    idempotencyKey: "\(idempotencyKey)_\(lot.id)_\(movements.count)"
                )
                movements.append(mov)
            }

            // 2. Trừ qua quy đổi
            if remainingNeeded > .zero {
                let targetConvs = findConversionsForTarget(ingredientId: req.ingredientId, conversions: conversions)
                for conv in targetConvs {
                    if remainingNeeded <= .zero { break }
                    if !UnitDimensions.areCompatible(conv.toUnit, req.unit) { continue }
                    let ratio = ExactDecimal(conv.ratio)

                    var rawIndices = clonedLots.indices.filter {
                        clonedLots[$0].ingredientId == conv.fromIngredientId &&
                        UnitDimensions.areCompatible(clonedLots[$0].unit, conv.fromUnit) &&
                        ExactDecimal(clonedLots[$0].remainingQuantity) > .zero
                    }
                    rawIndices.sort { lotSortKey(for: clonedLots[$0]) < lotSortKey(for: clonedLots[$1]) }

                    for idx in rawIndices {
                        if remainingNeeded <= .zero { break }
                        let lot = clonedLots[idx]
                        let lotRem = ExactDecimal(lot.remainingQuantity)

                        guard let neededInToUnit = try? UnitDimensions.convert(quantity: remainingNeeded, from: req.unit, to: conv.toUnit) else { continue }
                        let neededRawInFromUnit = neededInToUnit / ratio
                        guard let lotRawInFromUnit = try? UnitDimensions.convert(quantity: lotRem, from: lot.unit, to: conv.fromUnit) else { continue }

                        let takeRaw = lotRawInFromUnit < neededRawInFromUnit ? lotRawInFromUnit : neededRawInFromUnit
                        let takeLotUnit = (takeRaw == lotRawInFromUnit)
                            ? lotRem
                            : (try? UnitDimensions.convert(quantity: takeRaw, from: conv.fromUnit, to: lot.unit)) ?? lotRem

                        clonedLots[idx].remainingQuantity = (lotRem - takeLotUnit).description
                        let yieldedInToUnit = takeRaw * ratio
                        guard let yieldedReqUnit = try? UnitDimensions.convert(quantity: yieldedInToUnit, from: conv.toUnit, to: req.unit) else { continue }
                        remainingNeeded = remainingNeeded - yieldedReqUnit

                        if updatedLotsMap[lot.id] == nil {
                            updatedLotKeys.append(lot.id)
                        }
                        updatedLotsMap[lot.id] = clonedLots[idx]
                        let mov = StockMovement(
                            id: UUID().uuidString,
                            pantryLotId: lot.id,
                            quantityDelta: "-\(takeLotUnit.description)",
                            reason: "meal_consumption",
                            mealPlanId: mealPlanId,
                            idempotencyKey: "\(idempotencyKey)_\(lot.id)_\(movements.count)"
                        )
                        movements.append(mov)
                    }
                }
            }

            if remainingNeeded > .zero {
                deficits[req.ingredientId] = DeficitItem(
                    ingredientName: req.name,
                    missingQuantity: remainingNeeded.description,
                    unit: req.unit
                )
            }
        }

        let updatedLots = updatedLotKeys.compactMap { updatedLotsMap[$0] }
        return StockDeductionOutcome(updatedLots: updatedLots, movements: movements, deficits: deficits)
    }

    public static func deductRecipeStockFifo(
        pantryLots: [PantryLot],
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: [Conversion]? = nil
    ) throws -> (updatedLots: [PantryLot], movements: [StockMovement]) {
        let outcome = try executeStockDeduction(
            pantryLots: pantryLots,
            recipe: recipe,
            mealPlanId: mealPlanId,
            idempotencyKey: idempotencyKey,
            multiplier: multiplier,
            conversions: conversions,
            allowPartial: false
        )
        return (outcome.updatedLots, outcome.movements)
    }

    public static func deductRecipeStockAvailable(
        pantryLots: [PantryLot],
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: [Conversion]? = nil
    ) throws -> StockDeductionOutcome {
        return try executeStockDeduction(
            pantryLots: pantryLots,
            recipe: recipe,
            mealPlanId: mealPlanId,
            idempotencyKey: idempotencyKey,
            multiplier: multiplier,
            conversions: conversions,
            allowPartial: true
        )
    }

    public static func reverseStockMovements(
        pantryLots: [PantryLot],
        movements: [StockMovement],
        mealPlanId: String
    ) -> (restoredLots: [PantryLot], reversalMovements: [StockMovement]) {
        var lotMap = Dictionary(uniqueKeysWithValues: pantryLots.map { ($0.id, $0) })
        var restoredLotsMap: [String: PantryLot] = [:]
        var restoredLotKeys: [String] = []
        var reversalMovements: [StockMovement] = []

        let alreadyReversed = Set(
            movements
                .filter { ($0.idempotencyKey ?? "").hasPrefix("reversal_") }
                .compactMap { $0.idempotencyKey?.dropFirst("reversal_".count).description }
        )

        let targetMovements = movements.filter {
            $0.mealPlanId == mealPlanId &&
            $0.reason == "meal_consumption" &&
            ExactDecimal($0.quantityDelta) < .zero &&
            !alreadyReversed.contains($0.id)
        }

        for mov in targetMovements {
            guard var lot = lotMap[mov.pantryLotId] else { continue }
            let deltaAbs = ExactDecimal(mov.quantityDelta).abs()
            let currentRem = ExactDecimal(lot.remainingQuantity)
            let cap = ExactDecimal(lot.purchasedQuantity)
            let restored = currentRem + deltaAbs
            lot.remainingQuantity = (restored > cap ? cap : restored).description

            lotMap[lot.id] = lot
            if restoredLotsMap[lot.id] == nil {
                restoredLotKeys.append(lot.id)
            }
            restoredLotsMap[lot.id] = lot

            let revMov = StockMovement(
                id: UUID().uuidString,
                pantryLotId: lot.id,
                quantityDelta: deltaAbs.description,
                reason: "correction",
                mealPlanId: mealPlanId,
                idempotencyKey: "reversal_\(mov.id)"
            )
            reversalMovements.append(revMov)
        }

        let restoredLots = restoredLotKeys.compactMap { restoredLotsMap[$0] }
        return (restoredLots, reversalMovements)
    }

    /// Sổ cái phần dư của một mẻ nấu: mỗi mẻ nấu (≥ 4 khẩu phần) dư đúng một phần
    /// ăn, dùng lại một lần trong quá hạn (ngày nấu + leftoverDays).
    /// Khớp AvailableLeftover trong app/domain/planner.py và EasyMealsEngine.AvailableLeftover (Kotlin).
    /// (class — để `portionsRemaining` có thể giảm tại nơi khởi tạo.)
    public final class AvailableLeftover {
        public let dish: PlannedDish
        public var portionsRemaining: Int
        public let deadline: Date

        public init(dish: PlannedDish, portionsRemaining: Int, deadline: Date) {
            self.dish = dish
            self.portionsRemaining = portionsRemaining
            self.deadline = deadline
        }
    }

    /// Đồ dư dùng lại tối đa 2 ngày (mặc định), cấu hình được trong 1-3 ngày.
    public static func validateLeftoverDays(_ leftoverDays: Int) throws {
        guard leftoverDays >= PlanLimits.leftoverMinDays && leftoverDays <= PlanLimits.leftoverMaxDays else {
            throw IncompatibleUnitError(
                "Số ngày dùng lại đồ dư phải từ \(PlanLimits.leftoverMinDays) đến \(PlanLimits.leftoverMaxDays) ngày."
            )
        }
    }

    public static func generatePeriodPlan(
        startDateStr: String,
        endDateStr: String,
        recipes: [Recipe],
        currentPantryLots: [PantryLot],
        allowLeftovers: Bool = true,
        conversions: [Conversion]? = nil,
        rawIngredientNames: [String: String]? = nil,
        leftoverDays: Int = PlanLimits.leftoverDefaultDays,
        householdSettings: HouseholdSettings? = nil,
        recentlyCookedRecipeIds: Set<String> = [],
        avoidedIngredientIds: Set<String> = []
    ) throws -> (periodId: String, meals: [MealPlan], shoppingList: [ShoppingItem]) {
        try validateLeftoverDays(leftoverDays)
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone(secondsFromGMT: 0)

        guard let start = formatter.date(from: startDateStr),
              let end = formatter.date(from: endDateStr) else {
            throw IncompatibleUnitError("Định dạng ngày không hợp lệ (cần yyyy-MM-dd)")
        }

        let calendar = Calendar(identifier: .gregorian)
        let diff = calendar.dateComponents([.day], from: start, to: end).day ?? -1
        let diffDays = diff + 1

        guard diffDays >= PlanLimits.minDays && diffDays <= PlanLimits.maxDays else {
            throw IncompatibleUnitError("Số ngày lập thực đơn phải từ \(PlanLimits.minDays) đến \(PlanLimits.maxDays) ngày.")
        }

        let periodId = UUID().uuidString
        let eligibleRecipes = recipes.filter { recipe in !recipe.ingredients.contains { avoidedIngredientIds.contains($0.ingredientId) } }
        let excludedRecipes = recipes.filter { recipe in recipe.ingredients.contains { avoidedIngredientIds.contains($0.ingredientId) } }
        let recipesByCat: [String: [Recipe]] = [
            "man": eligibleRecipes.filter { $0.category == "man" },
            "rau": eligibleRecipes.filter { $0.category == "rau" },
            "canh": eligibleRecipes.filter { $0.category == "canh" }
        ]

        let simulatedLots = currentPantryLots
        var cookedRecipeIds = Set<String>()
        // Sổ cái phần dư: mỗi mẻ nấu (≥ 4 khẩu phần) dư số phần ăn theo kích thước hộ gia đình,
        // dùng lại một lần trong khoảng hạn (ngày nấu + leftoverDays). Khớp planner.py / Engine.kt.
        var availableLeftovers: [AvailableLeftover] = []
        var mealPlans: [MealPlan] = []
        var shoppingItemsMap: [String: ShoppingItem] = [:]

        // C1 - Vòng 13: cài đặt hộ gia đình cục bộ.
        let hs = householdSettings
        let householdSize = max(1, hs?.householdSize ?? 1)
        // Bữa cần lập mỗi ngày: ưu tiên cài đặt hộ gia đình, ngược lại trưa + tối.
        let resolvedPeriods: [String] = {
            guard let periods = hs?.mealPeriods, !periods.isEmpty else { return ["lunch", "dinner"] }
            return periods.map { $0.lowercased() }
        }()
        // Ngày không nấu / ăn ngoài: bỏ qua hoàn toàn khi lập kế hoạch.
        let skipDates = Set(hs?.skipDates ?? [])

        var curr = start

        // FIFO tiêu thụ PHẢI giữ qua các ngày lập kế hoạch (fixture
        // plan_fifo_consumption_persists_across_days): dùng MỘT mảng mutable duy nhất,
        // mỗi ngày chỉ lọc bớt lô đã hết hạn. Trước đây `usableLots` được filter lại từ
        // `simulatedLots` mỗi ngày (PantryLot là struct -> bản sao độc lập) làm tiêu thụ
        // của ngày trước bị mất -> ngày sau "còn đủ hàng" ngẫu nhiên, sai danh sách đi chợ.
        var carrying = simulatedLots

        for _ in 0..<diffDays {
            let dateStr = formatter.string(from: curr)
            // Ngày không nấu / ăn ngoài: bỏ qua hoàn toàn (không lập bữa, không trừ kho mô phỏng).
            if skipDates.contains(dateStr) {
                curr = calendar.date(byAdding: .day, value: 1, to: curr) ?? curr
                continue
            }
            // Lọc tại ngày lập: bỏ các lô đã quá hạn (tiêu thụ vẫn giữ qua ngày).
            carrying = carrying.filter { lot in
                guard let exp = lot.expiresAt else { return true }
                return exp >= dateStr
            }

            for p in resolvedPeriods {
                let planId = UUID().uuidString
                var plannedDishes: [PlannedDish] = []
                var planWarnings: [PlanWarning] = []

                for cat in ["man", "rau", "canh"] {
                    var dishChosen: PlannedDish?

                    // 1. Dùng thức ăn thừa (chỉ phần còn hạn và chưa dùng)
                    if allowLeftovers && !availableLeftovers.isEmpty {
                        if let idx = availableLeftovers.firstIndex(where: {
                            $0.portionsRemaining > 0
                                && (curr <= $0.deadline)
                                && $0.dish.category == cat
                        }) {
                            let entry = availableLeftovers.remove(at: idx)
                            entry.portionsRemaining -= 1
                            let left = entry.dish
                            dishChosen = PlannedDish(
                                id: UUID().uuidString,
                                mealPlanId: planId,
                                recipeId: left.recipeId,
                                recipeName: left.recipeName,
                                category: cat,
                                isLeftover: true,
                                originalDishId: left.id,
                                servings: left.servings,
                                // C2 - Vòng 13: diễn giải tại sao món này được chọn.
                                selectionReason: "Dùng đồ dư đã nấu trước"
                            )
                        }
                    }

                    // 2. Chọn món mới
                    if dishChosen == nil {
                        let candidates = (recipesByCat[cat] ?? []).filter { !cookedRecipeIds.contains($0.id) }
                        let rankedCandidates = candidates.sorted { lhs, rhs in
                            func score(_ recipe: Recipe) -> Double {
                                let requirements = aggregateRequirements(recipe: recipe)
                                var coverage = 0.0
                                var earliest: Date?
                                for req in requirements {
                                    let available = getTotalIngredientStock(pantryLots: carrying, ingredientId: req.ingredientId, targetUnit: req.unit, conversions: conversions)
                                    if req.quantity > .zero {
                                        coverage += min(1, Double((available / req.quantity).description) ?? 0)
                                    }
                                    for lot in carrying where lot.ingredientId == req.ingredientId && ExactDecimal(lot.remainingQuantity) > .zero {
                                        if let exp = lot.expiresAt, let date = formatter.date(from: exp), earliest == nil || date < earliest! { earliest = date }
                                    }
                                }
                                if !requirements.isEmpty { coverage /= Double(requirements.count) }
                                let days = earliest.map { max(0, min(30, calendar.dateComponents([.day], from: curr, to: $0).day ?? 30)) } ?? 30
                                let expiry = earliest == nil ? 0 : Double(30 - days) / 30
                                return coverage * 0.5 + expiry * 0.3 + (recentlyCookedRecipeIds.contains(recipe.id) ? 0 : 0.2)
                            }
                            return score(lhs) > score(rhs)
                        }
                        var fullyStocked: Recipe?
                        for r in rankedCandidates {
                            let (canCook, _) = checkRecipeStock(recipe: r, pantryLots: carrying, multiplier: "1", conversions: conversions)
                            if canCook {
                                fullyStocked = r
                                break
                            }
                        }

                        var chosen: Recipe?
                        if let stocked = fullyStocked {
                            chosen = stocked
                            for req in aggregateRequirements(recipe: stocked) {
                                _ = consumeAvailable(pantryLots: &carrying, ingredientId: req.ingredientId, quantity: req.quantity, unit: req.unit, conversions: conversions)
                            }
                        } else if let first = rankedCandidates.first {
                            chosen = first
                            let (_, deficits) = checkRecipeStock(recipe: first, pantryLots: carrying, multiplier: "1", conversions: conversions)
                            for req in aggregateRequirements(recipe: first) {
                                _ = consumeAvailable(pantryLots: &carrying, ingredientId: req.ingredientId, quantity: req.quantity, unit: req.unit, conversions: conversions)
                            }
                            for (ingId, def) in deficits {
                                var actualIngId = ingId
                                var actualUnit = def.unit
                                var actualQty = def.missingQuantity
                                var actualName = def.ingredientName

                                let targetConvs = findConversionsForTarget(ingredientId: ingId, conversions: conversions)
                                if let conv = targetConvs.first {
                                    let missingDecimal = ExactDecimal(def.missingQuantity)
                                    let missingInTo = (try? UnitDimensions.convert(quantity: missingDecimal, from: def.unit, to: conv.toUnit)) ?? missingDecimal
                                    let rawNeeded = missingInTo / ExactDecimal(conv.ratio)
                                    actualIngId = conv.fromIngredientId
                                    actualUnit = conv.fromUnit
                                    actualQty = rawNeeded.description
                                    actualName = rawIngredientNames?[actualIngId] ?? "Nguyên liệu gốc cho \(def.ingredientName)"
                                }

                                let dimStr = UnitDimensions.dimension(of: actualUnit)?.rawValue ?? "unknown"
                                let key = "\(actualIngId)|\(dimStr)"
                                if var item = shoppingItemsMap[key] {
                                    let missingDecimal = ExactDecimal(actualQty)
                                    let converted = (try? UnitDimensions.convert(quantity: missingDecimal, from: actualUnit, to: item.unit)) ?? missingDecimal
                                    item.neededQuantity = (ExactDecimal(item.neededQuantity) + converted).description
                                    if !item.dishNames.contains(first.name) {
                                        item.dishNames.append(first.name)
                                    }
                                    shoppingItemsMap[key] = item
                                } else {
                                    shoppingItemsMap[key] = ShoppingItem(
                                        ingredientId: actualIngId,
                                        ingredientName: actualName,
                                        neededQuantity: actualQty,
                                        unit: actualUnit,
                                        dishNames: [first.name]
                                    )
                                }
                            }
                        }

                        if let validChosen = chosen {
                            let chosenExpiry = aggregateRequirements(recipe: validChosen)
                                .flatMap { req in carrying.filter { $0.ingredientId == req.ingredientId }.compactMap { $0.expiresAt.flatMap(formatter.date(from:)) } }
                                .min()
                            let expiringSoon = chosenExpiry.map { (calendar.dateComponents([.day], from: curr, to: $0).day ?? 30) >= 0 && (calendar.dateComponents([.day], from: curr, to: $0).day ?? 30) <= 7 } ?? false
                            let dish = PlannedDish(
                                id: UUID().uuidString,
                                mealPlanId: planId,
                                recipeId: validChosen.id,
                                recipeName: validChosen.name,
                                category: cat,
                                isLeftover: false,
                                servings: validChosen.servings,
                                // C2 - Vòng 13: diễn giải tại sao món này được chọn.
                                selectionReason: expiringSoon
                                    ? "Ưu tiên dùng nguyên liệu sắp hết hạn trong tủ"
                                    : (fullyStocked != nil && !recentlyCookedRecipeIds.contains(validChosen.id)
                                    ? "Nguyên liệu đủ trong tủ, món chưa ăn gần đây"
                                    : (fullyStocked != nil ? "Nguyên liệu đủ trong tủ, nấu ngay" : "Chọn món thay thế, bổ sung vào danh sách đi chợ"))
                            )
                            dishChosen = dish
                            cookedRecipeIds.insert(validChosen.id)

                            if allowLeftovers && validChosen.servings >= 4 {
                                if let dead = calendar.date(byAdding: .day, value: leftoverDays, to: curr) {
                                    availableLeftovers.append(AvailableLeftover(dish: dish, portionsRemaining: householdSize, deadline: dead))
                                }
                            }
                        }
                    }

                    if dishChosen == nil && planWarnings.isEmpty && excludedRecipes.contains(where: { $0.category == cat }) {
                        planWarnings.append(PlanWarning(type: "not_enough_dishes", plannedFor: dateStr, mealPeriod: p, reason: "avoided_ingredients"))
                    }

                    if let d = dishChosen {
                        plannedDishes.append(d)
                    }
                }

                let plan = MealPlan(
                    id: planId,
                    plannedFor: dateStr,
                    mealPeriod: p,
                    periodId: periodId,
                    dishes: plannedDishes,
                    warnings: planWarnings
                )
                mealPlans.append(plan)
            }

            if let next = calendar.date(byAdding: .day, value: 1, to: curr) {
                curr = next
            }
        }

        return (periodId, mealPlans, Array(shoppingItemsMap.values))
    }

    /// Gộp đợt thực đơn mới vào thực đơn cũ an toàn (A2 - Vòng 13).
    /// Quy tắc khớp merge_new_plans_into_existing (planner.py):
    ///   - Bữa đã ăn luôn được giữ; bữa chưa ăn trong khoảng ngày mới bị thay;
    ///   - bữa chưa ăn ngoài khoảng ngày giữ nguyên; mọi bữa của đợt mới đều giữ.
    /// Bản ghi trùng id được khử (idempotency theo mã định danh bữa).
    public static func mergeNewPlansIntoExisting(
        _ existing: [MealPlan],
        newPlans: [MealPlan],
        mode: String = "replace"
    ) -> [MealPlan] {
        guard mode == "replace" || mode == "keep" else {
            fatalError("Chế độ gộp thực đơn không hợp lệ: \(mode)")
        }
        if newPlans.isEmpty { return existing }
        let rangeStart = newPlans.map(\.plannedFor).min() ?? ""
        let rangeEnd = newPlans.map(\.plannedFor).max() ?? ""

        var kept: [MealPlan] = []
        var seenIds = Set<String>()
        for plan in existing {
            if !seenIds.insert(plan.id).inserted { continue }
            if mode == "replace" && plan.eatenAt == nil &&
                plan.plannedFor >= rangeStart && plan.plannedFor <= rangeEnd {
                continue
            }
            kept.append(plan)
        }
        if mode == "keep" {
            let coveredDates = Set(existing.map(\.plannedFor))
            for plan in newPlans {
                if !seenIds.insert(plan.id).inserted { continue }
                if coveredDates.contains(plan.plannedFor) { continue }
                kept.append(plan)
            }
        } else {
            for plan in newPlans {
                if !seenIds.insert(plan.id).inserted { continue }
                kept.append(plan)
            }
        }
        return kept
    }

    public struct ShoppingBudgetResult: Equatable, Sendable {
        public let totalEstimatedBudget: String
        public let totalSpent: String
        public let itemsWithPriceCount: Int
        public let totalItemsCount: Int

        public init(
            totalEstimatedBudget: String,
            totalSpent: String,
            itemsWithPriceCount: Int,
            totalItemsCount: Int
        ) {
            self.totalEstimatedBudget = totalEstimatedBudget
            self.totalSpent = totalSpent
            self.itemsWithPriceCount = itemsWithPriceCount
            self.totalItemsCount = totalItemsCount
        }
    }

    public static func calculateShoppingBudget(_ items: [ShoppingItem]) -> ShoppingBudgetResult {
        var totalEstimated = ExactDecimal.zero
        var totalSpent = ExactDecimal.zero
        var itemsWithPrice = 0

        for it in items {
            if let pStr = it.price, !pStr.trimmingCharacters(in: .whitespaces).isEmpty {
                let p = ExactDecimal(pStr)
                if p > ExactDecimal.zero {
                    totalEstimated = totalEstimated + p
                    itemsWithPrice += 1
                    if it.isBought {
                        totalSpent = totalSpent + p
                    }
                }
            }
        }

        return ShoppingBudgetResult(
            totalEstimatedBudget: totalEstimated.description,
            totalSpent: totalSpent.description,
            itemsWithPriceCount: itemsWithPrice,
            totalItemsCount: items.count
        )
    }

    public static func groupShoppingItemsByCategory(
        _ items: [ShoppingItem],
        categoriesOrder: [String] = [
            "thit", "gia_cam", "hai_san", "trung_sua", "rau_cu",
            "cu_qua", "gao_bot_mi", "gia_vi", "nuoc_cham_dau", "khac"
        ]
    ) -> [String: [ShoppingItem]] {
        var grouped: [String: [ShoppingItem]] = [:]
        for c in categoriesOrder {
            grouped[c] = []
        }
        for it in items {
            let cat = it.category ?? "khac"
            if grouped[cat] != nil {
                grouped[cat]?.append(it)
            } else {
                if grouped["khac"] == nil {
                    grouped["khac"] = []
                }
                grouped["khac"]?.append(it)
            }
        }
        return grouped.filter { !$0.value.isEmpty }
    }

    public static func regenerateSingleMeal(
        targetMealPlanId: String,
        allMealPlans: [MealPlan],
        recipes: [Recipe],
        currentPantryLots: [PantryLot] = [],
        conversions: [Conversion] = [],
        avoidedIngredientIds: Set<String> = []
    ) throws -> MealPlan {
        guard let targetPlan = allMealPlans.first(where: { $0.id == targetMealPlanId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(targetMealPlanId)")
        }

        if targetPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món.")
        }

        var otherCookedRecipeIds = Set<String>()
        for p in allMealPlans {
            if p.id == targetMealPlanId { continue }
            for d in p.dishes {
                if !d.isLeftover {
                    otherCookedRecipeIds.insert(d.recipeId)
                }
            }
        }

        let eligibleRecipes = recipes.filter { recipe in !recipe.ingredients.contains { avoidedIngredientIds.contains($0.ingredientId) } }
        let excludedRecipes = recipes.filter { recipe in recipe.ingredients.contains { avoidedIngredientIds.contains($0.ingredientId) } }
        let recipesByCat: [String: [Recipe]] = [
            "man": eligibleRecipes.filter { $0.category == "man" },
            "rau": eligibleRecipes.filter { $0.category == "rau" },
            "canh": eligibleRecipes.filter { $0.category == "canh" }
        ]

        let planDateStr = String(targetPlan.plannedFor.prefix(10))
        var usableLots = currentPantryLots.filter { lot in
            guard let exp = lot.expiresAt else { return true }
            return exp >= planDateStr
        }

        var newDishes: [PlannedDish] = []
        for cat in ["man", "rau", "canh"] {
            var candidates = (recipesByCat[cat] ?? []).filter { !otherCookedRecipeIds.contains($0.id) }
            if candidates.isEmpty {
                candidates = (recipesByCat[cat] ?? []).filter { r in
                    !newDishes.contains { $0.recipeId == r.id }
                }
            }

            var chosen: Recipe?
            for r in candidates {
                let (canCook, _) = checkRecipeStock(recipe: r, pantryLots: usableLots, multiplier: "1", conversions: conversions)
                if canCook {
                    chosen = r
                    break
                }
            }
            if chosen == nil, !candidates.isEmpty {
                chosen = candidates.first
            }

            if let r = chosen {
                for req in aggregateRequirements(recipe: r) {
                    _ = consumeAvailable(
                        pantryLots: &usableLots,
                        ingredientId: req.ingredientId,
                        quantity: req.quantity,
                        unit: req.unit,
                        conversions: conversions
                    )
                }
                newDishes.append(
                    PlannedDish(
                        id: UUID().uuidString,
                        mealPlanId: targetPlan.id,
                        recipeId: r.id,
                        recipeName: r.name,
                        category: cat,
                        isLeftover: false,
                        originalDishId: nil,
                        servings: r.servings
                    )
                )
            }
        }

        let warnings = excludedRecipes.contains { excluded in newDishes.allSatisfy { $0.category != excluded.category } }
            ? [PlanWarning(type: "not_enough_dishes", plannedFor: targetPlan.plannedFor, mealPeriod: targetPlan.mealPeriod, reason: "avoided_ingredients")]
            : []
        return MealPlan(
            id: targetPlan.id,
            plannedFor: targetPlan.plannedFor,
            mealPeriod: targetPlan.mealPeriod,
            periodId: targetPlan.periodId,
            eatenAt: nil,
            dishes: newDishes,
            warnings: warnings
        )
    }

    public static func recomputeShoppingList(
        mealPlans: [MealPlan],
        currentPantryLots: [PantryLot] = [],
        recipes: [Recipe] = [],
        conversions: [Conversion] = [],
        rawIngredientNames: [String: String] = [:],
        ingredientCategories: [String: String] = [:]
    ) -> [ShoppingItem] {
        let recipesMap = Dictionary(uniqueKeysWithValues: recipes.map { ($0.id, $0) })
        var simulatedLots = currentPantryLots
        var shoppingItemsMap: [String: ShoppingItem] = [:]

        let uneatenPlans = mealPlans.filter { $0.eatenAt == nil }
            .sorted { $0.plannedFor < $1.plannedFor }

        for meal in uneatenPlans {
            let mealDateStr = String(meal.plannedFor.prefix(10))
            simulatedLots = simulatedLots.filter { lot in
                guard let exp = lot.expiresAt else { return true }
                return exp >= mealDateStr
            }

            for dish in meal.dishes {
                if dish.isLeftover { continue }
                guard let recipe = recipesMap[dish.recipeId] else { continue }

                let (_, deficits) = checkRecipeStock(recipe: recipe, pantryLots: simulatedLots, multiplier: "1", conversions: conversions)
                for req in aggregateRequirements(recipe: recipe) {
                    _ = consumeAvailable(
                        pantryLots: &simulatedLots,
                        ingredientId: req.ingredientId,
                        quantity: req.quantity,
                        unit: req.unit,
                        conversions: conversions
                    )
                }

                for (ingId, def) in deficits {
                    let actualIngId: String
                    let actualUnit: String
                    let actualQty: String
                    let actualName: String

                    let targetConvs = findConversionsForTarget(ingredientId: ingId, conversions: conversions)
                    if let conv = targetConvs.first {
                        let missingInTo = try! UnitDimensions.convert(quantity: ExactDecimal(def.missingQuantity), from: def.unit, to: conv.toUnit)
                        let rawNeeded = missingInTo / ExactDecimal(conv.ratio)
                        actualIngId = conv.fromIngredientId
                        actualUnit = conv.fromUnit
                        actualQty = rawNeeded.description
                        actualName = rawIngredientNames[actualIngId] ?? "Nguyên liệu gốc cho \(def.ingredientName)"
                    } else {
                        actualIngId = ingId
                        actualUnit = def.unit
                        actualQty = def.missingQuantity
                        actualName = def.ingredientName
                    }

                    let dim = UnitDimensions.dimension(of: actualUnit)?.rawValue ?? actualUnit
                    let key = "\(actualIngId)_\(dim)"
                    let cat = ingredientCategories[actualIngId] ?? "khac"

                    if var existing = shoppingItemsMap[key] {
                        let added = try! UnitDimensions.convert(quantity: ExactDecimal(actualQty), from: actualUnit, to: existing.unit)
                        let sum = ExactDecimal(existing.neededQuantity) + added
                        existing.neededQuantity = sum.description
                        if !existing.dishNames.contains(recipe.name) {
                            existing.dishNames.append(recipe.name)
                        }
                        shoppingItemsMap[key] = existing
                    } else {
                        shoppingItemsMap[key] = ShoppingItem(
                            ingredientId: actualIngId,
                            ingredientName: actualName,
                            neededQuantity: actualQty,
                            unit: actualUnit,
                            isBought: false,
                            isManuallyAdded: false,
                            dishNames: [recipe.name],
                            category: cat
                        )
                    }
                }
            }
        }

        return Array(shoppingItemsMap.values)
    }

    public static func swapDishInMeal(
        mealPlan: MealPlan,
        oldDishId: String,
        newRecipe: Recipe,
        allPlansInPeriod: [MealPlan] = []
    ) throws -> MealPlan {
        if mealPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món.")
        }
        var dishes = mealPlan.dishes
        guard let dishIdx = dishes.firstIndex(where: { $0.id == oldDishId }) else {
            throw MealPlanError("Không tìm thấy món có ID \(oldDishId) trong bữa ăn.")
        }

        if !allPlansInPeriod.isEmpty {
            let otherRecipeIds = Set(
                allPlansInPeriod.flatMap { $0.dishes }
                    .filter { !$0.isLeftover && ($0.mealPlanId != mealPlan.id || $0.id != oldDishId) }
                    .map { $0.recipeId }
            )
            if otherRecipeIds.contains(newRecipe.id) {
                throw MealPlanError("Món '\(newRecipe.name)' đã được lên lịch trong chu kỳ thực đơn này.")
            }
        }

        dishes[dishIdx] = PlannedDish(
            id: UUID().uuidString,
            mealPlanId: mealPlan.id,
            recipeId: newRecipe.id,
            recipeName: newRecipe.name,
            category: newRecipe.category,
            isLeftover: false,
            servings: newRecipe.servings
        )
        var copy = mealPlan
        copy.dishes = dishes
        return copy
    }

    public static func addDishToMeal(
        mealPlan: MealPlan,
        recipe: Recipe,
        servings: Int? = nil
    ) throws -> MealPlan {
        if mealPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn thêm món.")
        }
        if mealPlan.dishes.contains(where: { $0.recipeId == recipe.id }) {
            throw MealPlanError("Món '\(recipe.name)' đã có trong bữa ăn này.")
        }
        let catCount = mealPlan.dishes.filter { $0.category == recipe.category }.count
        if catCount >= 2 {
            throw MealPlanError("Bữa ăn đã đạt giới hạn tối đa 2 món cho nhóm \(recipe.category).")
        }

        var copy = mealPlan
        copy.dishes.append(
            PlannedDish(
                id: UUID().uuidString,
                mealPlanId: mealPlan.id,
                recipeId: recipe.id,
                recipeName: recipe.name,
                category: recipe.category,
                isLeftover: false,
                servings: servings ?? recipe.servings
            )
        )
        return copy
    }

    public static func removeDishFromMeal(
        mealPlan: MealPlan,
        dishId: String
    ) throws -> MealPlan {
        if mealPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn bỏ món.")
        }
        guard let dishIdx = mealPlan.dishes.firstIndex(where: { $0.id == dishId }) else {
            throw MealPlanError("Không tìm thấy món có ID \(dishId) trong bữa ăn.")
        }
        if mealPlan.dishes.count <= 1 {
            throw MealPlanError("Không thể bỏ món duy nhất còn lại trong bữa ăn.")
        }
        var copy = mealPlan
        copy.dishes.remove(at: dishIdx)
        return copy
    }

    public static func rescheduleMeal(
        mealPlan: MealPlan,
        newDateStr: String,
        newPeriod: String,
        allMealPlans: [MealPlan]
    ) throws -> MealPlan {
        if mealPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn chuyển ngày/bữa.")
        }
        let targetDate = String(newDateStr.prefix(10))
        let conflict = allMealPlans.contains {
            $0.id != mealPlan.id &&
            String($0.plannedFor.prefix(10)) == targetDate &&
            $0.mealPeriod == newPeriod
        }
        if conflict {
            let periodVn = newPeriod == "lunch" ? "trưa" : "tối"
            throw MealPlanError("Đã có bữa ăn khác được lên lịch vào bữa \(periodVn) ngày \(newDateStr).")
        }
        return MealPlan(
            id: mealPlan.id,
            plannedFor: targetDate,
            mealPeriod: newPeriod,
            periodId: mealPlan.periodId,
            eatenAt: mealPlan.eatenAt,
            dishes: mealPlan.dishes
        )
    }

    public static func mergeCompatibleShoppingItems(_ items: [ShoppingItem]) throws -> [ShoppingItem] {
        var mergedMap: [String: ShoppingItem] = [:]

        for it in items {
            let dim = UnitDimensions.dimension(of: it.unit)?.rawValue ?? it.unit
            let key = "\(it.ingredientId)_\(dim)"

            if var existing = mergedMap[key] {
                let converted = try UnitDimensions.convert(quantity: ExactDecimal(it.neededQuantity), from: it.unit, to: existing.unit)
                existing.neededQuantity = (ExactDecimal(existing.neededQuantity) + converted).description

                for dn in it.dishNames {
                    if !existing.dishNames.contains(dn) {
                        existing.dishNames.append(dn)
                    }
                }

                if let p = it.price, existing.price == nil {
                    existing.price = p
                } else if let p1 = it.price, let p2 = existing.price {
                    existing.price = (ExactDecimal(p2) + ExactDecimal(p1)).description
                }

                existing.isBought = existing.isBought && it.isBought
                mergedMap[key] = existing
            } else {
                mergedMap[key] = it
            }
        }

        return Array(mergedMap.values)
    }
}
