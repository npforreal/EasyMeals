import Foundation
import Observation

@Observable
public final class AppStorage: @unchecked Sendable {
    public static let shared = AppStorage()

    public var ingredients: [Ingredient] = []
    public var recipes: [Recipe] = []
    public var conversions: [Conversion] = []
    public var pantryLots: [PantryLot] = []
    public var mealPlans: [MealPlan] = []
    public var stockMovements: [StockMovement] = []
    public var shoppingItems: [ShoppingItem] = []
    public var catalogueVersion: String = "2026.10.26"
    public var loadError: String? = nil

    // Trạng thái snackbar hoàn tác
    public var undoMessage: String?
    public var lastActionPlanId: String?

    private let fileManager = FileManager.default
    private var dataDirectory: URL {
        fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }
    private var storageFileURL: URL {
        dataDirectory.appendingPathComponent("easymeals_local_state.json")
    }

    public init() {
        loadCatalogue()
        loadPersistedState()
    }

    public func loadCatalogue() {
        if let bundle = CatalogueLoader.shared.loadBundledCatalogue() {
            self.ingredients = bundle.ingredients
            self.recipes = bundle.recipes
            self.conversions = bundle.conversions
            self.catalogueVersion = bundle.version
            self.loadError = nil
        } else {
            self.loadError = "Không thể nạp danh mục món ăn. Vui lòng thử lại."
        }
    }

    // MARK: - Pantry Operations
    public func addPantryLot(
        ingredientId: String,
        ingredientName: String,
        quantity: String,
        unit: String,
        expiresAt: String? = nil,
        purchasedAt: String? = ISO8601DateFormatter().string(from: Date()).prefix(10).description
    ) {
        let lot = PantryLot(
            ingredientId: ingredientId,
            ingredientName: ingredientName,
            remainingQuantity: quantity,
            purchasedQuantity: quantity,
            unit: unit,
            purchasedAt: purchasedAt,
            expiresAt: expiresAt
        )
        pantryLots.insert(lot, at: 0)
        persistState()
    }

    public func removePantryLot(id: String) {
        pantryLots.removeAll { $0.id == id }
        persistState()
    }

    public func extendPantryLotExpiry(id: String, daysToAdd: Int = 3) {
        if let idx = pantryLots.firstIndex(where: { $0.id == id }) {
            let old = pantryLots[idx]
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            let baseDate = (old.expiresAt.flatMap { formatter.date(from: $0) }) ?? Date()
            if let newDate = Calendar.current.date(byAdding: .day, value: daysToAdd, to: baseDate) {
                pantryLots[idx] = PantryLot(
                    id: old.id,
                    ingredientId: old.ingredientId,
                    ingredientName: old.ingredientName,
                    remainingQuantity: old.remainingQuantity,
                    purchasedQuantity: old.purchasedQuantity,
                    unit: old.unit,
                    purchasedAt: old.purchasedAt,
                    expiresAt: formatter.string(from: newDate),
                    location: old.location
                )
                persistState()
            }
        }
    }

    public func updatePantryLotQuantity(id: String, newQuantity: String) {
        if let idx = pantryLots.firstIndex(where: { $0.id == id }) {
            pantryLots[idx].remainingQuantity = newQuantity
            persistState()
        }
    }

    // MARK: - Meal Plan & "Đã ăn" FIFO Action
    public func checkMealStock(planId: String) -> (canEat: Bool, deficits: [String: DeficitItem]) {
        guard let plan = mealPlans.first(where: { $0.id == planId }) else { return (true, [:]) }
        var allDeficits: [String: DeficitItem] = [:]

        for dish in plan.dishes {
            if dish.isLeftover { continue }
            guard let recipe = recipes.first(where: { $0.id == dish.recipeId }) else { continue }
            let mult = (ExactDecimal(dish.servings) / ExactDecimal(recipe.servings)).description
            let (canCook, deficits) = EasyMealsEngine.checkRecipeStock(
                recipe: recipe,
                pantryLots: pantryLots,
                multiplier: mult,
                conversions: conversions
            )
            if !canCook {
                for (k, v) in deficits {
                    if let existing = allDeficits[k] {
                        let sumMissing = ExactDecimal(existing.missingQuantity) + ExactDecimal(v.missingQuantity)
                        allDeficits[k] = DeficitItem(
                            ingredientName: existing.ingredientName,
                            missingQuantity: sumMissing.description,
                            unit: existing.unit
                        )
                    } else {
                        allDeficits[k] = v
                    }
                }
            }
        }
        return (allDeficits.isEmpty, allDeficits)
    }

    public func eatMeal(planId: String, allowPartial: Bool = false) throws {
        guard let planIdx = mealPlans.firstIndex(where: { $0.id == planId }) else { return }
        let plan = mealPlans[planIdx]
        if plan.eatenAt != nil { return } // Đã ăn rồi, bỏ qua bảo vệ double-tap

        if !allowPartial {
            let (canEat, deficits) = checkMealStock(planId: planId)
            if !canEat {
                throw InsufficientStockError("Không đủ nguyên liệu để nấu bữa ăn này", deficits: deficits)
            }
        }

        var currentPantry = pantryLots
        var allMovs = stockMovements

        for dish in plan.dishes {
            if dish.isLeftover { continue }
            if let recipe = recipes.first(where: { $0.id == dish.recipeId }) {
                let mult = (ExactDecimal(dish.servings) / ExactDecimal(recipe.servings)).description
                let outcome = try EasyMealsEngine.executeStockDeduction(
                    pantryLots: currentPantry,
                    recipe: recipe,
                    mealPlanId: planId,
                    idempotencyKey: "mobile_eat_\(planId)_\(dish.recipeId)",
                    multiplier: mult,
                    conversions: conversions,
                    allowPartial: allowPartial
                )
                // Cập nhật tồn kho
                for u in outcome.updatedLots {
                    if let idx = currentPantry.firstIndex(where: { $0.id == u.id }) {
                        currentPantry[idx] = u
                    }
                }
                allMovs.append(contentsOf: outcome.movements)
            }
        }

        pantryLots = currentPantry
        stockMovements = allMovs
        mealPlans[planIdx].eatenAt = ISO8601DateFormatter().string(from: Date())
        lastActionPlanId = planId
        undoMessage = "Đã ghi nhận bữa ăn và trừ kho!"
        persistState()
    }

    public func addDeficitsToShoppingList(deficits: [DeficitItem]) {
        for d in deficits {
            let matching = ingredients.first { $0.name.lowercased() == d.ingredientName.lowercased() }
            let ingId = matching?.id ?? UUID().uuidString
            let item = ShoppingItem(
                ingredientId: ingId,
                ingredientName: d.ingredientName,
                neededQuantity: d.missingQuantity,
                unit: d.unit,
                // Người dùng tự bấm thêm -> giữ khi kế hoạch đổi (A3).
                isManuallyAdded: true
            )
            shoppingItems.append(item)
        }
        persistState()
    }

    public func undoLastEatMeal() {
        guard let planId = lastActionPlanId,
              let planIdx = mealPlans.firstIndex(where: { $0.id == planId }) else {
            return
        }

        let (restored, revMovs) = EasyMealsEngine.reverseStockMovements(
            pantryLots: pantryLots,
            movements: stockMovements,
            mealPlanId: planId
        )

        for r in restored {
            if let idx = pantryLots.firstIndex(where: { $0.id == r.id }) {
                pantryLots[idx] = r
            }
        }
        stockMovements.append(contentsOf: revMovs)
        mealPlans[planIdx].eatenAt = nil

        lastActionPlanId = nil
        undoMessage = "Đã hoàn tác và khôi phục nguyên liệu!"
        persistState()
    }

    // MARK: - Shopping List Operations
    public func toggleShoppingItem(id: String) {
        if let idx = shoppingItems.firstIndex(where: { $0.id == id }) {
            shoppingItems[idx].isBought.toggle()
            persistState()
        }
    }

    /// Nhóm nguyên liệu trong catalogue (không thấy -> nil -> mặc định "khác").
    public func categoryOf(ingredientId: String) -> String? {
        return ingredients.first { $0.id == ingredientId }?.category
    }

    public func addCustomShoppingItem(name: String, quantity: String, unit: String) {        let matchingIng = ingredients.first { $0.name.lowercased() == name.lowercased() }
        let ingId = matchingIng?.id ?? UUID().uuidString
        let item = ShoppingItem(
            ingredientId: ingId,
            ingredientName: name,
            neededQuantity: quantity,
            unit: unit,
            // Người dùng tự thêm -> giữ khi kế hoạch đổi (A3).
            isManuallyAdded: true
        )
        shoppingItems.append(item)
        persistState()
    }

    public func bulkAddBoughtToPantry(overrides: [PurchaseOverride] = []) {
        // A4: mua vào tủ chính xác — lượng thực mua có thể khác ước tính, hạn dùng
        // mặc định theo nhóm nguyên liệu; idempotent theo id mục (chống bấm lặp).
        let boughtItems = shoppingItems.filter { $0.isBought }
        let ovById = Dictionary(uniqueKeysWithValues: overrides.map { ($0.itemId, $0) })
        let purchasedAt = Date()

        func dateOnly(_ iso: String) -> String {
            return String(iso.prefix(10))
        }

        for item in boughtItems {
            let ov = ovById[item.id]
            let qty = ov?.actualQuantity.trimmingCharacters(in: .whitespaces).isEmpty == false
                ? ov!.actualQuantity.trimmingCharacters(in: .whitespaces) : item.neededQuantity
            guard let parsed = Double(qty.replacingOccurrences(of: ",", with: ".")), parsed > 0 else {
                continue // lượng vô nghĩa: không tạo lot rác
            }
            let category = ingredients.first { $0.id == item.ingredientId }?.category
            let expiresAt: String
            let ovExpiry = ov?.expiresAt.trimmingCharacters(in: .whitespaces) ?? ""
            if !ovExpiry.isEmpty {
                expiresAt = ovExpiry
            } else {
                let named = dateOnly(ShoppingDefaults.expiryDate(category: category, purchasedAt: purchasedAt))
                expiresAt = named
            }
            addPantryLot(
                ingredientId: item.ingredientId,
                ingredientName: item.ingredientName,
                quantity: qty,
                unit: item.unit,
                expiresAt: expiresAt
            )
        }
        // Giao dịch cập nhật danh sách: chỉ xoá các mục vẫn còn trong danh sách.
        let boughtIds = Set(boughtItems.map { $0.id })
        shoppingItems.removeAll { boughtIds.contains($0.id) }
        persistState()
    }

    // MARK: - Lập thực đơn tự động
    /// Đợt mới có trùng bữa CHƯA ăn trong khoảng ngày [hôm nay, hôm nay + days - 1]? (A2)
    public func hasUneatenOverlap(days: Int = 3) -> Bool {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone(secondsFromGMT: 0)

        guard
            let end = Calendar.current.date(byAdding: .day, value: days - 1, to: Date())
        else { return false }
        let start = formatter.string(from: Date())
        let endStr = formatter.string(from: end)
        return mealPlans.contains {
            $0.eatenAt == nil && $0.plannedFor >= start && $0.plannedFor <= endStr
        }
    }

    /**
     * Tạo đợt thực đơn mới an toàn (A2): gộp qua engine theo mode giữ/thay.
     * Bữa đã ăn và bữa ngoài khoảng ngày được giữ nguyên, không xoá lịch sử kho.
     */
    public func generateNewPlan(
        days: Int = 3,
        mergeMode: String = "replace",
        allowLeftovers: Bool = true,
        leftoverDays: Int = PlanLimits.leftoverDefaultDays
    ) {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone(secondsFromGMT: 0)

        let start = Date()
        guard let end = Calendar.current.date(byAdding: .day, value: days - 1, to: start) else { return }

        let startStr = formatter.string(from: start)
        let endStr = formatter.string(from: end)

        if let result = try? EasyMealsEngine.generatePeriodPlan(
            startDateStr: startStr,
            endDateStr: endStr,
            recipes: recipes,
            currentPantryLots: pantryLots,
            allowLeftovers: allowLeftovers,
            // A7 - Vòng 13: truyền quy đổi đơn vị/nguyên liệu (gạo -> cơm) kèm tên
            // nguyên liệu gốc để danh sách mua nêu "Gạo", khớp mọi đường chạy khác.
            conversions: conversions,
            rawIngredientNames: Dictionary(
                uniqueKeysWithValues: ingredients.map { ($0.id, $0.name) }
            ),
            leftoverDays: leftoverDays
        ) {
            self.mealPlans = EasyMealsEngine.mergeNewPlansIntoExisting(
                mealPlans,
                newPlans: result.meals,
                mode: mergeMode
            )
            // A3: thay toàn bộ mục sinh tự của đợt mới nhưng GIỮ mục người dùng tự thêm.
            let manual = shoppingItems.filter { $0.isManuallyAdded }
            let manualKeys = Set(manual.map { $0.id })
            self.shoppingItems = manual + result.shoppingList.filter { !manualKeys.contains($0.id) }
            persistState()
        }
    }

    // MARK: - Backup & Restore
    public func exportBackupData() throws -> Data {
        let payload = BackupPayload(
            appVersion: "2.0.0",
            exportedAt: ISO8601DateFormatter().string(from: Date()),
            pantryLots: pantryLots,
            mealPlans: mealPlans,
            stockMovements: stockMovements,
            shoppingItems: shoppingItems
        )
        return try BackupManager.encode(payload: payload)
    }

    public func importBackupData(_ data: Data, replace: Bool = true) throws {
        let payload = try BackupManager.validateAndDecode(jsonData: data)
        if replace {
            self.pantryLots = payload.pantryLots
            self.mealPlans = payload.mealPlans
            self.stockMovements = payload.stockMovements
            self.shoppingItems = payload.shoppingItems
        } else {
            // Chế độ gộp: nối thêm lô tủ và món đi chợ
            let existingLotIds = Set(pantryLots.map { $0.id })
            for lot in payload.pantryLots where !existingLotIds.contains(lot.id) {
                pantryLots.append(lot)
            }
            let existingShopIds = Set(shoppingItems.map { $0.id })
            for item in payload.shoppingItems where !existingShopIds.contains(item.id) {
                shoppingItems.append(item)
            }
        }
        persistState()
    }

    public func wipeAllData() {
        pantryLots.removeAll()
        mealPlans.removeAll()
        stockMovements.removeAll()
        shoppingItems.removeAll()
        lastActionPlanId = nil
        undoMessage = nil
        try? fileManager.removeItem(at: storageFileURL)
    }

    // MARK: - Local Persistence
    private struct PersistedState: Codable {
        let pantryLots: [PantryLot]
        let mealPlans: [MealPlan]
        let stockMovements: [StockMovement]
        let shoppingItems: [ShoppingItem]
    }

    private func persistState() {
        let state = PersistedState(
            pantryLots: pantryLots,
            mealPlans: mealPlans,
            stockMovements: stockMovements,
            shoppingItems: shoppingItems
        )
        if let data = try? JSONEncoder().encode(state) {
            try? data.write(to: storageFileURL, options: .atomic)
        }
    }

    private func loadPersistedState() {
        guard let data = try? Data(contentsOf: storageFileURL),
              let state = try? JSONDecoder().decode(PersistedState.self, from: data) else {
            return
        }
        self.pantryLots = state.pantryLots
        self.mealPlans = state.mealPlans
        self.stockMovements = state.stockMovements
        self.shoppingItems = state.shoppingItems
    }
}
