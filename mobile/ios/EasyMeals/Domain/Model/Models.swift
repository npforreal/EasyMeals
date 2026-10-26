import Foundation

public enum UnitDimension: String, Codable, Sendable {
    case mass
    case volume
    case count
}

public struct Category: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let displayOrder: Int

    public init(id: String, name: String, displayOrder: Int = 0) {
        self.id = id
        self.name = name
        self.displayOrder = displayOrder
    }

    enum CodingKeys: String, CodingKey {
        case id, name
        case displayOrder = "display_order"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try c.decode(String.self, forKey: .id)
        self.name = try c.decode(String.self, forKey: .name)
        self.displayOrder = try c.decodeIfPresent(Int.self, forKey: .displayOrder) ?? 0
    }
}

public struct Conversion: Codable, Equatable, Sendable {
    public let fromIngredientId: String
    public let toIngredientId: String
    public let ratio: String
    public let fromUnit: String
    public let toUnit: String
    public let note: String?

    public init(
        fromIngredientId: String,
        toIngredientId: String,
        ratio: String,
        fromUnit: String = "g",
        toUnit: String = "g",
        note: String? = nil
    ) {
        self.fromIngredientId = fromIngredientId
        self.toIngredientId = toIngredientId
        self.ratio = ratio
        self.fromUnit = fromUnit
        self.toUnit = toUnit
        self.note = note
    }

    enum CodingKeys: String, CodingKey {
        case fromIngredientId = "from_ingredient_id"
        case toIngredientId = "to_ingredient_id"
        case ratio
        case fromUnit = "from_unit"
        case toUnit = "to_unit"
        case note
    }
}

public struct Ingredient: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let normalizedName: String
    public var category: String
    public var defaultUnit: String
    public let aliases: [String]
    public let allergens: [String]
    public let allergenVerificationStatus: String
    public let allergenSourceURL: String?
    public let allergenVerifiedAt: String?

    public init(id: String, name: String, normalizedName: String, category: String = "khac", defaultUnit: String = "g", aliases: [String] = [], allergens: [String] = [], allergenVerificationStatus: String = "unknown", allergenSourceURL: String? = nil, allergenVerifiedAt: String? = nil) {
        self.id = id
        self.name = name
        self.normalizedName = normalizedName
        self.category = category
        self.defaultUnit = defaultUnit
        self.aliases = aliases
        self.allergens = allergens
        self.allergenVerificationStatus = allergenVerificationStatus
        self.allergenSourceURL = allergenSourceURL
        self.allergenVerifiedAt = allergenVerifiedAt
    }

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case normalizedName = "normalized_name"
        case category
        case defaultUnit = "default_unit"
        case aliases
        case allergens
        case allergenVerificationStatus = "allergen_verification_status"
        case allergenSourceURL = "allergen_source_url"
        case allergenVerifiedAt = "allergen_verified_at"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(String.self, forKey: .id)
        self.name = try container.decode(String.self, forKey: .name)
        self.normalizedName = try container.decodeIfPresent(String.self, forKey: .normalizedName) ?? ""
        self.category = try container.decodeIfPresent(String.self, forKey: .category) ?? "khac"
        self.defaultUnit = try container.decodeIfPresent(String.self, forKey: .defaultUnit) ?? "g"
        self.aliases = try container.decodeIfPresent([String].self, forKey: .aliases) ?? []
        self.allergens = try container.decodeIfPresent([String].self, forKey: .allergens) ?? []
        self.allergenVerificationStatus = try container.decodeIfPresent(String.self, forKey: .allergenVerificationStatus) ?? "unknown"
        self.allergenSourceURL = try container.decodeIfPresent(String.self, forKey: .allergenSourceURL)
        self.allergenVerifiedAt = try container.decodeIfPresent(String.self, forKey: .allergenVerifiedAt)
    }
}

public struct RecipeIngredient: Identifiable, Codable, Equatable, Sendable {
    public var id: String { "\(ingredientId)_\(unit)" }
    public let ingredientId: String
    public let ingredientName: String
    public let quantity: String
    public let unit: String

    public init(ingredientId: String, ingredientName: String, quantity: String, unit: String) {
        self.ingredientId = ingredientId
        self.ingredientName = ingredientName
        self.quantity = quantity
        self.unit = unit
    }

    enum CodingKeys: String, CodingKey {
        case ingredientId = "ingredient_id"
        case ingredientName = "ingredient_name"
        case quantity
        case unit
    }
}

public struct Recipe: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let category: String
    public let servings: Int
    public let instructions: [String]
    public let ingredients: [RecipeIngredient]
    public let dietaryStatus: String
    public let dietarySourceURL: String?
    public let dietaryVerifiedAt: String?
    public let spiceLevel: Int?
    public let spiceSourceURL: String?
    public let spiceVerifiedAt: String?

    public init(id: String, name: String, category: String, servings: Int = 4, instructions: [String] = [], ingredients: [RecipeIngredient] = [], dietaryStatus: String = "unknown", dietarySourceURL: String? = nil, dietaryVerifiedAt: String? = nil, spiceLevel: Int? = nil, spiceSourceURL: String? = nil, spiceVerifiedAt: String? = nil) {
        self.id = id
        self.name = name
        self.category = category
        self.servings = servings
        self.instructions = instructions
        self.ingredients = ingredients
        self.dietaryStatus = dietaryStatus
        self.dietarySourceURL = dietarySourceURL
        self.dietaryVerifiedAt = dietaryVerifiedAt
        self.spiceLevel = spiceLevel
        self.spiceSourceURL = spiceSourceURL
        self.spiceVerifiedAt = spiceVerifiedAt
    }

    enum CodingKeys: String, CodingKey {
        case id, name, category, servings, instructions, ingredients
        case dietaryStatus = "dietary_status"
        case dietarySourceURL = "dietary_source_url"
        case dietaryVerifiedAt = "dietary_verified_at"
        case spiceLevel = "spice_level"
        case spiceSourceURL = "spice_source_url"
        case spiceVerifiedAt = "spice_verified_at"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(String.self, forKey: .id)
        self.name = try container.decode(String.self, forKey: .name)
        self.category = try container.decode(String.self, forKey: .category)
        self.servings = try container.decodeIfPresent(Int.self, forKey: .servings) ?? 4
        self.instructions = try container.decodeIfPresent([String].self, forKey: .instructions) ?? []
        self.ingredients = try container.decodeIfPresent([RecipeIngredient].self, forKey: .ingredients) ?? []
        self.dietaryStatus = try container.decodeIfPresent(String.self, forKey: .dietaryStatus) ?? "unknown"
        self.dietarySourceURL = try container.decodeIfPresent(String.self, forKey: .dietarySourceURL)
        self.dietaryVerifiedAt = try container.decodeIfPresent(String.self, forKey: .dietaryVerifiedAt)
        self.spiceLevel = try container.decodeIfPresent(Int.self, forKey: .spiceLevel)
        self.spiceSourceURL = try container.decodeIfPresent(String.self, forKey: .spiceSourceURL)
        self.spiceVerifiedAt = try container.decodeIfPresent(String.self, forKey: .spiceVerifiedAt)
    }
}

public struct PantryLot: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let ingredientId: String
    public let ingredientName: String
    public var remainingQuantity: String
    public let purchasedQuantity: String
    public let unit: String
    public let purchasedAt: String?
    public let expiresAt: String?
    public let location: String?

    public init(
        id: String = UUID().uuidString,
        ingredientId: String,
        ingredientName: String,
        remainingQuantity: String,
        purchasedQuantity: String,
        unit: String,
        purchasedAt: String? = nil,
        expiresAt: String? = nil,
        location: String? = "fridge"
    ) {
        self.id = id
        self.ingredientId = ingredientId
        self.ingredientName = ingredientName
        self.remainingQuantity = remainingQuantity
        self.purchasedQuantity = purchasedQuantity
        self.unit = unit
        self.purchasedAt = purchasedAt
        self.expiresAt = expiresAt
        self.location = location
    }

    enum CodingKeys: String, CodingKey {
        case id
        case ingredientId = "ingredient_id"
        case ingredientName = "ingredient_name"
        case remainingQuantity = "remaining_quantity"
        case purchasedQuantity = "purchased_quantity"
        case unit
        case purchasedAt = "purchased_at"
        case expiresAt = "expires_at"
        case location
    }
}

public struct StockMovement: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let pantryLotId: String
    public let quantityDelta: String
    public let reason: String
    public let mealPlanId: String?
    public let idempotencyKey: String?
    public let createdAt: String

    public init(
        id: String = UUID().uuidString,
        pantryLotId: String,
        quantityDelta: String,
        reason: String,
        mealPlanId: String? = nil,
        idempotencyKey: String? = nil,
        createdAt: String = ISO8601DateFormatter().string(from: Date())
    ) {
        self.id = id
        self.pantryLotId = pantryLotId
        self.quantityDelta = quantityDelta
        self.reason = reason
        self.mealPlanId = mealPlanId
        self.idempotencyKey = idempotencyKey
        self.createdAt = createdAt
    }

    enum CodingKeys: String, CodingKey {
        case id
        case pantryLotId = "pantry_lot_id"
        case quantityDelta = "quantity_delta"
        case reason
        case mealPlanId = "meal_plan_id"
        case idempotencyKey = "idempotency_key"
        case createdAt = "created_at"
    }
}

public struct PlannedDish: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let mealPlanId: String?
    public let recipeId: String
    public let recipeName: String
    public let category: String
    public let isLeftover: Bool
    public let originalDishId: String?
    public let servings: Int
    // C2 - Vòng 13: diễn giải tại sao món này được chọn.
    public var selectionReason: String?

    public init(
        id: String = UUID().uuidString,
        mealPlanId: String? = nil,
        recipeId: String,
        recipeName: String,
        category: String,
        isLeftover: Bool = false,
        originalDishId: String? = nil,
        servings: Int = 4,
        selectionReason: String? = nil
    ) {
        self.id = id
        self.mealPlanId = mealPlanId
        self.recipeId = recipeId
        self.recipeName = recipeName
        self.category = category
        self.isLeftover = isLeftover
        self.originalDishId = originalDishId
        self.servings = servings
        self.selectionReason = selectionReason
    }

    enum CodingKeys: String, CodingKey {
        case id
        case mealPlanId = "meal_plan_id"
        case recipeId = "recipe_id"
        case recipeName = "recipe_name"
        case category
        case isLeftover = "is_leftover"
        case originalDishId = "original_dish_id"
        case servings
        case selectionReason = "selection_reason"
    }
}

public struct MealPlan: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let plannedFor: String
    public let mealPeriod: String
    public let periodId: String?
    public var eatenAt: String?
    public var notes: String?
    public var dishes: [PlannedDish]

    public init(
        id: String = UUID().uuidString,
        plannedFor: String,
        mealPeriod: String,
        periodId: String? = nil,
        eatenAt: String? = nil,
        notes: String? = nil,
        dishes: [PlannedDish] = []
    ) {
        self.id = id
        self.plannedFor = plannedFor
        self.mealPeriod = mealPeriod
        self.periodId = periodId
        self.eatenAt = eatenAt
        self.notes = notes
        self.dishes = dishes
    }

    enum CodingKeys: String, CodingKey {
        case id
        case plannedFor = "planned_for"
        case mealPeriod = "meal_period"
        case periodId = "period_id"
        case eatenAt = "eaten_at"
        case notes
        case dishes
    }
}

public struct ShoppingItem: Identifiable, Codable, Equatable, Sendable {
    public var id: String { "\(ingredientId)_\(unit)" }
    public let ingredientId: String
    public let ingredientName: String
    public var neededQuantity: String
    public let unit: String
    public var isBought: Bool
    // A3 - Vòng 13: nguồn phát sinh — người dùng tự thêm thì giữ khi kế hoạch đổi.
    public var isManuallyAdded: Bool
    public var dishNames: [String]
    public var category: String?
    public var price: String?
    public var boughtQuantity: String?

    public init(
        ingredientId: String,
        ingredientName: String,
        neededQuantity: String,
        unit: String,
        isBought: Bool = false,
        isManuallyAdded: Bool = false,
        dishNames: [String] = [],
        category: String? = "khac",
        price: String? = nil,
        boughtQuantity: String? = nil
    ) {
        self.ingredientId = ingredientId
        self.ingredientName = ingredientName
        self.neededQuantity = neededQuantity
        self.unit = unit
        self.isBought = isBought
        self.isManuallyAdded = isManuallyAdded
        self.dishNames = dishNames
        self.category = category
        self.price = price
        self.boughtQuantity = boughtQuantity
    }

    enum CodingKeys: String, CodingKey {
        case ingredientId = "ingredient_id"
        case ingredientName = "ingredient_name"
        case neededQuantity = "needed_quantity"
        case unit
        case isBought = "is_bought"
        case isManuallyAdded = "is_manually_added"
        case dishNames = "dish_names"
        case category
        case price
        case boughtQuantity = "bought_quantity"
    }

    /// A3: decode tương thích — bản state/backup cũ thiếu `is_manually_added` (và cả
    /// `is_bought`/`dish_names`/`price`/`category`) về giá trị mặc định thay vì văng lỗi giải mã.
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        ingredientId = try container.decode(String.self, forKey: .ingredientId)
        ingredientName = try container.decode(String.self, forKey: .ingredientName)
        neededQuantity = try container.decode(String.self, forKey: .neededQuantity)
        unit = try container.decode(String.self, forKey: .unit)
        isBought = try container.decodeIfPresent(Bool.self, forKey: .isBought) ?? false
        isManuallyAdded = try container.decodeIfPresent(Bool.self, forKey: .isManuallyAdded) ?? false
        dishNames = try container.decodeIfPresent([String].self, forKey: .dishNames) ?? []
        category = try container.decodeIfPresent(String.self, forKey: .category) ?? "khac"
        price = try container.decodeIfPresent(String.self, forKey: .price)
        boughtQuantity = try container.decodeIfPresent(String.self, forKey: .boughtQuantity)
    }
}

public struct DeficitItem: Codable, Equatable, Sendable {
    public let ingredientName: String
    public let missingQuantity: String
    public let unit: String

    public init(ingredientName: String, missingQuantity: String, unit: String) {
        self.ingredientName = ingredientName
        self.missingQuantity = missingQuantity
        self.unit = unit
    }

    enum CodingKeys: String, CodingKey {
        case ingredientName = "ingredient_name"
        case missingQuantity = "missing_quantity"
        case unit
    }
}

// C1 - Vòng 13: cài đặt hộ gia đình cục bộ (không lưu lên server).
public struct HouseholdSettings: Codable, Equatable, Sendable {
    public let householdSize: Int
    public let defaultServings: Int
    public let mealPeriods: [String]
    public let skipDates: [String]
    public let planDays: Int

    public init(
        householdSize: Int = 1,
        defaultServings: Int = 2,
        mealPeriods: [String] = ["lunch", "dinner"],
        skipDates: [String] = [],
        planDays: Int = PlanLimits.defaultDays
    ) {
        self.householdSize = householdSize
        self.defaultServings = defaultServings
        self.mealPeriods = mealPeriods
        self.skipDates = skipDates
        self.planDays = planDays
    }

    enum CodingKeys: String, CodingKey {
        case householdSize = "household_size"
        case defaultServings = "default_servings"
        case mealPeriods = "meal_periods"
        case skipDates = "skip_dates"
        case planDays = "plan_days"
    }
}
