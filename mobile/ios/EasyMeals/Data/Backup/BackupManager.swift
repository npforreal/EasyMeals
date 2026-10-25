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

    /// A3: decode tương thích — bản sao lưu cũ thiếu `shopping_items`
    /// (hoặc các khối khác) về danh sách rỗng thay vì văng lỗi khi nhập.
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        appVersion = try container.decodeIfPresent(String.self, forKey: .appVersion) ?? "2.0.0"
        exportedAt = try container.decodeIfPresent(String.self, forKey: .exportedAt) ?? ""
        pantryLots = try container.decodeIfPresent([PantryLot].self, forKey: .pantryLots) ?? []
        mealPlans = try container.decodeIfPresent([MealPlan].self, forKey: .mealPlans) ?? []
        stockMovements = try container.decodeIfPresent([StockMovement].self, forKey: .stockMovements) ?? []
        shoppingItems = try container.decodeIfPresent([ShoppingItem].self, forKey: .shoppingItems) ?? []
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
