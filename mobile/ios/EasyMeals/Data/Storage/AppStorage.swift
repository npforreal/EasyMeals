import Foundation
import Observation

@Observable
public final class AppStorage: @unchecked Sendable {
    public static let shared = AppStorage()

    public var ingredients: [Ingredient] = []
    public var recipes: [Recipe] = []
    public var pantryLots: [PantryLot] = []
    public var mealPlans: [MealPlan] = []
    public var stockMovements: [StockMovement] = []
    public var shoppingItems: [ShoppingItem] = []
    public var catalogueVersion: String = "2026.10.26"

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
            self.catalogueVersion = bundle.version
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

    public func updatePantryLotQuantity(id: String, newQuantity: String) {
        if let idx = pantryLots.firstIndex(where: { $0.id == id }) {
            pantryLots[idx].remainingQuantity = newQuantity
            persistState()
        }
    }

    // MARK: - Meal Plan & "Đã ăn" FIFO Action
    public func eatMeal(planId: String) throws {
        guard let planIdx = mealPlans.firstIndex(where: { $0.id == planId }) else { return }
        let plan = mealPlans[planIdx]
        if plan.eatenAt != nil { return } // Đã ăn rồi, bỏ qua bảo vệ double-tap

        for dish in plan.dishes {
            if dish.isLeftover { continue }
            if let recipe = recipes.first(where: { $0.id == dish.recipeId }) {
                let (updated, movs) = try EasyMealsEngine.deductRecipeStockFifo(
                    pantryLots: pantryLots,
                    recipe: recipe,
                    mealPlanId: planId,
                    idempotencyKey: "mobile_eat_\(planId)"
                )
                // Cập nhật tồn kho
                for u in updated {
                    if let idx = pantryLots.firstIndex(where: { $0.id == u.id }) {
                        pantryLots[idx] = u
                    }
                }
                stockMovements.append(contentsOf: movs)
            }
        }

        mealPlans[planIdx].eatenAt = ISO8601DateFormatter().string(from: Date())
        lastActionPlanId = planId
        undoMessage = "Đã ghi nhận bữa ăn và trừ kho!"
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

    public func addCustomShoppingItem(name: String, quantity: String, unit: String) {
        let matchingIng = ingredients.first { $0.name.lowercased() == name.lowercased() }
        let ingId = matchingIng?.id ?? UUID().uuidString
        let item = ShoppingItem(
            ingredientId: ingId,
            ingredientName: name,
            neededQuantity: quantity,
            unit: unit
        )
        shoppingItems.append(item)
        persistState()
    }

    public func bulkAddBoughtToPantry() {
        let boughtItems = shoppingItems.filter { $0.isBought }
        for item in boughtItems {
            addPantryLot(
                ingredientId: item.ingredientId,
                ingredientName: item.ingredientName,
                quantity: item.neededQuantity,
                unit: item.unit
            )
        }
        shoppingItems.removeAll { $0.isBought }
        persistState()
    }

    // MARK: - Lập thực đơn tự động
    public func generateNewPlan(days: Int = 3) {
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
            allowLeftovers: true
        ) {
            self.mealPlans = result.meals
            self.shoppingItems = result.shoppingList
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
