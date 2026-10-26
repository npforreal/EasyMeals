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

    // C1 - Vòng 13: cài đặt hộ gia đình cục bộ (không lưu lên server, nhưng backup/restore cùng state).
    public var householdSize: Int = 1
    public var defaultServings: Int = 2
    public var mealPeriods: [String] = ["lunch", "dinner"]
    public var skipDates: [String] = []
    public var planDays: Int = PlanLimits.defaultDays

    public var householdSettings: HouseholdSettings {
        HouseholdSettings(
            householdSize: householdSize,
            defaultServings: defaultServings,
            mealPeriods: mealPeriods,
            skipDates: skipDates,
            planDays: planDays
        )
    }

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

    public func updateMealNotes(planId: String, notes: String) {
        guard notes.count <= 500,
              let index = mealPlans.firstIndex(where: { $0.id == planId }),
              mealPlans[index].eatenAt == nil else { return }
        mealPlans[index].notes = notes.isEmpty ? nil : notes
        persistState()
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

    public func updateShoppingItemPrice(id: String, price: String?) {
        if let idx = shoppingItems.firstIndex(where: { $0.id == id }) {
            let p = price?.trimmingCharacters(in: .whitespaces)
            shoppingItems[idx].price = (p?.isEmpty == false) ? p : nil
            persistState()
        }
    }

    public func updateShoppingItem(
        id: String,
        quantity: String? = nil,
        unit: String? = nil,
        price: String? = nil
    ) {
        if let idx = shoppingItems.firstIndex(where: { $0.id == id }) {
            if let q = quantity?.trimmingCharacters(in: .whitespaces), !q.isEmpty {
                shoppingItems[idx].neededQuantity = q
            }
            if let u = unit?.trimmingCharacters(in: .whitespaces), !u.isEmpty {
                // If unit changes, need to update id? id is a computed property "\(ingredientId)_\(unit)" in ShoppingItem!
            }
            if let p = price?.trimmingCharacters(in: .whitespaces) {
                shoppingItems[idx].price = p.isEmpty ? nil : p
            }
            persistState()
        }
    }

    public func mergeShoppingItems() throws {
        self.shoppingItems = try EasyMealsEngine.mergeCompatibleShoppingItems(shoppingItems)
        persistState()
    }

    public func deleteShoppingItem(id: String) {
        shoppingItems.removeAll { $0.id == id }
        persistState()
    }

    /// Nhóm nguyên liệu trong catalogue (không thấy -> nil -> mặc định "khac").
    public func categoryOf(ingredientId: String) -> String? {
        return ingredients.first { $0.id == ingredientId }?.category
    }

    public func addCustomShoppingItem(
        name: String,
        quantity: String,
        unit: String,
        category: String = "khac",
        price: String? = nil
    ) {
        let matchingIng = ingredients.first { $0.name.lowercased() == name.lowercased() }
        let ingId = matchingIng?.id ?? UUID().uuidString
        let p = price?.trimmingCharacters(in: .whitespaces)
        let item = ShoppingItem(
            ingredientId: ingId,
            ingredientName: name,
            neededQuantity: quantity,
            unit: unit,
            isBought: false,
            isManuallyAdded: true,
            dishNames: [],
            category: category,
            price: (p?.isEmpty == false) ? p : nil
        )
        shoppingItems.append(item)
        persistState()
    }

    // C1 - Vòng 13: setters cài đặt hộ gia đình (lưu vào tệp trạng thái cục bộ).
    public func setHouseholdSize(_ size: Int) {
        householdSize = max(1, min(20, size))
        persistState()
    }

    public func setDefaultServings(_ servings: Int) {
        defaultServings = max(1, min(50, servings))
        persistState()
    }

    public func setMealPeriods(_ periods: [String]) {
        mealPeriods = periods.filter { ["breakfast", "lunch", "dinner"].contains($0) }
        if mealPeriods.isEmpty { mealPeriods = ["lunch", "dinner"] }
        persistState()
    }

    public func setSkipDates(_ dates: [String]) {
        skipDates = dates
        persistState()
    }

    public func setPlanDays(_ days: Int) {
        planDays = max(PlanLimits.minDays, min(PlanLimits.maxDays, days))
        persistState()
    }

    public func regenerateMeal(planId: String) throws {
        guard let targetIdx = mealPlans.firstIndex(where: { $0.id == planId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(planId)")
        }
        let targetPlan = mealPlans[targetIdx]
        if targetPlan.eatenAt != nil {
            throw MealPlanError("Bữa ăn này đã được đánh dấu ăn, không thể sinh lại.")
        }
        let updatedMeal = try EasyMealsEngine.regenerateSingleMeal(
            targetMealPlanId: planId,
            allMealPlans: mealPlans,
            recipes: recipes,
            currentPantryLots: pantryLots,
            conversions: conversions
        )
        mealPlans[targetIdx] = updatedMeal

        let rawNames = Dictionary(uniqueKeysWithValues: ingredients.map { ($0.id, $0.name) })
        let ingCats = Dictionary(uniqueKeysWithValues: ingredients.map { ($0.id, $0.category) })
        let planShopping = EasyMealsEngine.recomputeShoppingList(
            mealPlans: mealPlans,
            currentPantryLots: pantryLots,
            recipes: recipes,
            conversions: conversions,
            rawIngredientNames: rawNames,
            ingredientCategories: ingCats
        )

        let manual = shoppingItems.filter { $0.isManuallyAdded }
        let manualKeys = Set(manual.map { $0.id })
        let oldMap = Dictionary(uniqueKeysWithValues: shoppingItems.map { ($0.ingredientId + "_" + $0.unit, $0) })

        let mergedPlanItems = planShopping.filter { !manualKeys.contains($0.id) }.map { item -> ShoppingItem in
            let key = item.ingredientId + "_" + item.unit
            if let old = oldMap[key] {
                var copy = item
                copy.price = old.price
                copy.isBought = old.isBought
                return copy
            }
            return item
        }

        self.shoppingItems = manual + mergedPlanItems
        persistState()
    }

    public func swapDish(mealPlanId: String, oldDishId: String, newRecipeId: String) throws {
        guard let targetIdx = mealPlans.firstIndex(where: { $0.id == mealPlanId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(mealPlanId)")
        }
        guard let recipe = recipes.first(where: { $0.id == newRecipeId }) else {
            throw MealPlanError("Không tìm thấy món có ID \(newRecipeId)")
        }
        let updatedMeal = try EasyMealsEngine.swapDishInMeal(
            mealPlan: mealPlans[targetIdx],
            oldDishId: oldDishId,
            newRecipe: recipe,
            allPlansInPeriod: mealPlans
        )
        mealPlans[targetIdx] = updatedMeal
        updateShoppingListAfterPlanChange()
        persistState()
    }

    public func addDish(mealPlanId: String, recipeId: String, servings: Int? = nil) throws {
        guard let targetIdx = mealPlans.firstIndex(where: { $0.id == mealPlanId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(mealPlanId)")
        }
        guard let recipe = recipes.first(where: { $0.id == recipeId }) else {
            throw MealPlanError("Không tìm thấy món có ID \(recipeId)")
        }
        let updatedMeal = try EasyMealsEngine.addDishToMeal(
            mealPlan: mealPlans[targetIdx],
            recipe: recipe,
            servings: servings
        )
        mealPlans[targetIdx] = updatedMeal
        updateShoppingListAfterPlanChange()
        persistState()
    }

    public func removeDish(mealPlanId: String, dishId: String) throws {
        guard let targetIdx = mealPlans.firstIndex(where: { $0.id == mealPlanId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(mealPlanId)")
        }
        let updatedMeal = try EasyMealsEngine.removeDishFromMeal(
            mealPlan: mealPlans[targetIdx],
            dishId: dishId
        )
        mealPlans[targetIdx] = updatedMeal
        updateShoppingListAfterPlanChange()
        persistState()
    }

    public func rescheduleMeal(mealPlanId: String, newDateStr: String, newPeriod: String) throws {
        guard let targetIdx = mealPlans.firstIndex(where: { $0.id == mealPlanId }) else {
            throw MealPlanError("Không tìm thấy bữa ăn có ID \(mealPlanId)")
        }
        let updatedMeal = try EasyMealsEngine.rescheduleMeal(
            mealPlan: mealPlans[targetIdx],
            newDateStr: newDateStr,
            newPeriod: newPeriod,
            allMealPlans: mealPlans
        )
        mealPlans[targetIdx] = updatedMeal
        updateShoppingListAfterPlanChange()
        persistState()
    }

    private func updateShoppingListAfterPlanChange() {
        let rawNames = Dictionary(uniqueKeysWithValues: ingredients.map { ($0.id, $0.name) })
        let ingCats = Dictionary(uniqueKeysWithValues: ingredients.map { ($0.id, $0.category) })
        let planShopping = EasyMealsEngine.recomputeShoppingList(
            mealPlans: mealPlans,
            currentPantryLots: pantryLots,
            recipes: recipes,
            conversions: conversions,
            rawIngredientNames: rawNames,
            ingredientCategories: ingCats
        )

        let manual = shoppingItems.filter { $0.isManuallyAdded }
        let manualKeys = Set(manual.map { $0.id })
        let oldMap = Dictionary(uniqueKeysWithValues: shoppingItems.map { ($0.ingredientId + "_" + $0.unit, $0) })

        let mergedPlanItems = planShopping.filter { !manualKeys.contains($0.id) }.map { item -> ShoppingItem in
            let key = item.ingredientId + "_" + item.unit
            if let old = oldMap[key] {
                var copy = item
                copy.price = old.price
                copy.isBought = old.isBought
                return copy
            }
            return item
        }
        self.shoppingItems = manual + mergedPlanItems
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
            leftoverDays: leftoverDays,
            // C1 - Vòng 13: truyền cài đặt hộ gia đình cục bộ vào engine.
            householdSettings: self.householdSettings
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
        // C1 - Vòng 13: cài đặt hộ gia đình (tùy chọn để tương thích backup cũ).
        let householdSettings: HouseholdSettings?
    }

    private func persistState() {
        let state = PersistedState(
            pantryLots: pantryLots,
            mealPlans: mealPlans,
            stockMovements: stockMovements,
            shoppingItems: shoppingItems,
            householdSettings: self.householdSettings
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
        if let hs = state.householdSettings {
            self.householdSize = hs.householdSize
            self.defaultServings = hs.defaultServings
            self.mealPeriods = hs.mealPeriods
            self.skipDates = hs.skipDates
            self.planDays = hs.planDays
        }
    }
}
