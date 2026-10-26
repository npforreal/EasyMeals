import Foundation

public struct BackupPayload: Codable, Sendable {
    public let schemaVersion: Int
    public let appVersion: String
    public let exportedAt: String
    public let pantryLots: [PantryLot]
    public let mealPlans: [MealPlan]
    public let stockMovements: [StockMovement]
    public let shoppingItems: [ShoppingItem]
    public let recipePreferences: RecipePreferencesBackup

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case appVersion = "app_version"
        case exportedAt = "exported_at"
        case pantryLots = "pantry_lots"
        case mealPlans = "meal_plans"
        case stockMovements = "stock_movements"
        case shoppingItems = "shopping_items"
        case recipePreferences = "recipe_preferences"
    }

    public init(
        appVersion: String = "2.0.0",
        exportedAt: String = ISO8601DateFormatter().string(from: Date()),
        pantryLots: [PantryLot] = [],
        mealPlans: [MealPlan] = [],
        stockMovements: [StockMovement] = [],
        shoppingItems: [ShoppingItem] = [],
        schemaVersion: Int = 2,
        recipePreferences: RecipePreferencesBackup = RecipePreferencesBackup()
    ) {
        self.schemaVersion = schemaVersion
        self.appVersion = appVersion
        self.exportedAt = exportedAt
        self.pantryLots = pantryLots
        self.mealPlans = mealPlans
        self.stockMovements = stockMovements
        self.shoppingItems = shoppingItems
        self.recipePreferences = recipePreferences
    }

    /// A3: decode tương thích — bản sao lưu cũ thiếu `shopping_items`
    /// (hoặc các khối khác) về danh sách rỗng thay vì văng lỗi khi nhập.
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decodeIfPresent(Int.self, forKey: .schemaVersion) ?? 1
        appVersion = try container.decodeIfPresent(String.self, forKey: .appVersion) ?? "2.0.0"
        exportedAt = try container.decodeIfPresent(String.self, forKey: .exportedAt) ?? ""
        pantryLots = try container.decodeIfPresent([PantryLot].self, forKey: .pantryLots) ?? []
        mealPlans = try container.decodeIfPresent([MealPlan].self, forKey: .mealPlans) ?? []
        stockMovements = try container.decodeIfPresent([StockMovement].self, forKey: .stockMovements) ?? []
        shoppingItems = try container.decodeIfPresent([ShoppingItem].self, forKey: .shoppingItems) ?? []
        recipePreferences = try container.decodeIfPresent(RecipePreferencesBackup.self, forKey: .recipePreferences) ?? RecipePreferencesBackup()
    }
}

public struct RecipePreferencesBackup: Codable, Sendable, Equatable {
    public var avoidedIngredientIds: [String]
    public var preferredIngredientIds: [String]
    public var dietaryFilter: String
    public var maxSpice: Int

    enum CodingKeys: String, CodingKey {
        case avoidedIngredientIds = "avoided_ingredient_ids"
        case preferredIngredientIds = "preferred_ingredient_ids"
        case dietaryFilter = "dietary_filter"
        case maxSpice = "max_spice"
    }

    public init(avoidedIngredientIds: [String] = [], preferredIngredientIds: [String] = [], dietaryFilter: String = "", maxSpice: Int = -1) {
        self.avoidedIngredientIds = avoidedIngredientIds
        self.preferredIngredientIds = preferredIngredientIds
        self.dietaryFilter = dietaryFilter
        self.maxSpice = maxSpice
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        avoidedIngredientIds = try container.decodeIfPresent([String].self, forKey: .avoidedIngredientIds) ?? []
        preferredIngredientIds = try container.decodeIfPresent([String].self, forKey: .preferredIngredientIds) ?? []
        dietaryFilter = try container.decodeIfPresent(String.self, forKey: .dietaryFilter) ?? ""
        maxSpice = try container.decodeIfPresent(Int.self, forKey: .maxSpice) ?? -1
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
