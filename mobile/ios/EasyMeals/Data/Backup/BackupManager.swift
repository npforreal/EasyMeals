import Foundation

public struct BackupPayload: Codable, Sendable {
    public let appVersion: String
    public let exportedAt: String
    public let pantryLots: [PantryLot]
    public let mealPlans: [MealPlan]
    public let stockMovements: [StockMovement]
    public let shoppingItems: [ShoppingItem]

    enum CodingKeys: String, CodingKey {
        case appVersion = "app_version"
        case exportedAt = "exported_at"
        case pantryLots = "pantry_lots"
        case mealPlans = "meal_plans"
        case stockMovements = "stock_movements"
        case shoppingItems = "shopping_items"
    }

    public init(
        appVersion: String = "2.0.0",
        exportedAt: String = ISO8601DateFormatter().string(from: Date()),
        pantryLots: [PantryLot] = [],
        mealPlans: [MealPlan] = [],
        stockMovements: [StockMovement] = [],
        shoppingItems: [ShoppingItem] = []
    ) {
        self.appVersion = appVersion
        self.exportedAt = exportedAt
        self.pantryLots = pantryLots
        self.mealPlans = mealPlans
        self.stockMovements = stockMovements
        self.shoppingItems = shoppingItems
    }
}

public enum BackupManager {
    public static func validateAndDecode(jsonData: Data) throws -> BackupPayload {
        // Bảo vệ chống JSON bomb (giới hạn 10MB)
        guard jsonData.count <= 10 * 1024 * 1024 else {
            throw IncompatibleUnitError("Kích thước file sao lưu vượt quá giới hạn 10MB.")
        }

        let decoder = JSONDecoder()
        return try decoder.decode(BackupPayload.self, from: jsonData)
    }

    public static func encode(payload: BackupPayload) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(payload)
    }
}
