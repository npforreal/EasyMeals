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
        appVersion: String = BackupManager.appVersion,
        exportedAt: String = ISO8601DateFormatter().string(from: Date()),
        pantryLots: [PantryLot] = [],
        mealPlans: [MealPlan] = [],
        stockMovements: [StockMovement] = [],
        shoppingItems: [ShoppingItem] = [],
        schemaVersion: Int = BackupManager.schemaVersion,
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
        appVersion = try container.decodeIfPresent(String.self, forKey: .appVersion) ?? BackupManager.appVersion
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
    /// F1 thêm khoá ngoại movements; F3 thêm thông tin phiên bản và đọc chéo định dạng Web.
    public static let schemaVersion = 3
    public static let appVersion = "2.0.0"
    private static let maxBytes = 10 * 1024 * 1024

    public static func validateAndDecode(jsonData: Data) throws -> BackupPayload {
        // Bảo vệ chống JSON bomb (giới hạn 10MB)
        guard jsonData.count <= maxBytes else {
            throw IncompatibleUnitError("Kích thước file sao lưu vượt quá giới hạn 10MB.")
        }

        let normalized = try normalizeToMobileShape(jsonData)
        let payload: BackupPayload
        do {
            payload = try JSONDecoder().decode(BackupPayload.self, from: normalized)
        } catch {
            throw IncompatibleUnitError(
                "Không đọc được bản sao lưu: cấu trúc dữ liệu không khớp (\(error.localizedDescription)). " +
                "Hãy thử xuất lại bản sao lưu từ ứng dụng."
            )
        }

        if payload.schemaVersion > schemaVersion {
            throw IncompatibleUnitError(
                "Bản sao lưu dùng schema \(payload.schemaVersion), ứng dụng chỉ hỗ trợ đến \(schemaVersion). " +
                "Hãy cập nhật EasyMeals lên bản mới rồi thử lại."
            )
        }
        return payload
    }

    public static func encode(payload: BackupPayload) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(payload)
    }

    /// F3: nhận cả định dạng phẳng của ứng dụng di động và định dạng `data.*` của bản Web.
    private static func normalizeToMobileShape(_ data: Data) throws -> Data {
        let root: [String: Any]
        do {
            guard let parsed = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw IncompatibleUnitError("File sao lưu không đúng định dạng JSON hợp lệ.")
            }
            root = parsed
        } catch let error as IncompatibleUnitError {
            throw error
        } catch {
            throw IncompatibleUnitError(
                "Không đọc được JSON: \(error.localizedDescription). Hãy kiểm tra tệp có bị cắt ngắn không."
            )
        }

        guard let webData = root["data"] as? [String: Any] else {
            return data
        }

        var mapped: [String: Any] = [:]
        if let version = root["schema_version"] { mapped["schema_version"] = version }
        if let version = root["app_version"] { mapped["app_version"] = version }
        if let exported = root["exported_at"] { mapped["exported_at"] = exported }
        if let pantry = webData["pantry"] { mapped["pantry_lots"] = pantry }
        if let plans = webData["plans"] { mapped["meal_plans"] = plans }
        if let movements = webData["movements"] { mapped["stock_movements"] = movements }
        if let shopping = webData["shopping"] { mapped["shopping_items"] = shopping }

        // Tuỳ chọn công thức của Web nằm trong settings với khoá recipe_preferences_v1.
        if let settings = webData["settings"] as? [[String: Any]],
           let entry = settings.first(where: { $0["key"] as? String == "recipe_preferences_v1" }),
           let value = entry["value"] as? [String: Any] {
            var prefs: [String: Any] = [:]
            if let avoided = value["avoidedIngredientIds"] { prefs["avoided_ingredient_ids"] = avoided }
            if let preferred = value["preferredIngredientIds"] { prefs["preferred_ingredient_ids"] = preferred }
            if let dietary = value["dietaryFilter"] { prefs["dietary_filter"] = dietary }
            if let spice = value["maxSpice"] { prefs["max_spice"] = spice }
            mapped["recipe_preferences"] = prefs
        }

        return try JSONSerialization.data(withJSONObject: mapped)
    }
}
