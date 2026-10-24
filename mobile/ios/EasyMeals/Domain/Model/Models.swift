import Foundation

public enum UnitDimension: String, Codable, Sendable {
    case mass
    case volume
    case count
}

public struct Ingredient: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let normalizedName: String
    public let category: String
    public let defaultUnit: String

    public init(id: String, name: String, normalizedName: String, category: String, defaultUnit: String) {
        self.id = id
        self.name = name
        self.normalizedName = normalizedName
        self.category = category
        self.defaultUnit = defaultUnit
    }

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case normalizedName = "normalized_name"
        case category
        case defaultUnit = "default_unit"
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

    public init(id: String, name: String, category: String, servings: Int = 4, instructions: [String] = [], ingredients: [RecipeIngredient] = []) {
        self.id = id
        self.name = name
        self.category = category
        self.servings = servings
        self.instructions = instructions
        self.ingredients = ingredients
    }

    enum CodingKeys: String, CodingKey {
        case id, name, category, servings, instructions, ingredients
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(String.self, forKey: .id)
        self.name = try container.decode(String.self, forKey: .name)
        self.category = try container.decode(String.self, forKey: .category)
        self.servings = try container.decodeIfPresent(Int.self, forKey: .servings) ?? 4
        self.instructions = try container.decodeIfPresent([String].self, forKey: .instructions) ?? []
        self.ingredients = try container.decodeIfPresent([RecipeIngredient].self, forKey: .ingredients) ?? []
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

    public init(
        id: String = UUID().uuidString,
        mealPlanId: String? = nil,
        recipeId: String,
        recipeName: String,
        category: String,
        isLeftover: Bool = false,
        originalDishId: String? = nil,
        servings: Int = 4
    ) {
        self.id = id
        self.mealPlanId = mealPlanId
        self.recipeId = recipeId
        self.recipeName = recipeName
        self.category = category
        self.isLeftover = isLeftover
        self.originalDishId = originalDishId
        self.servings = servings
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
    }
}

public struct MealPlan: Identifiable, Codable, Equatable, Sendable {
    public let id: String
    public let plannedFor: String
    public let mealPeriod: String
    public let periodId: String?
    public var eatenAt: String?
    public var dishes: [PlannedDish]

    public init(
        id: String = UUID().uuidString,
        plannedFor: String,
        mealPeriod: String,
        periodId: String? = nil,
        eatenAt: String? = nil,
        dishes: [PlannedDish] = []
    ) {
        self.id = id
        self.plannedFor = plannedFor
        self.mealPeriod = mealPeriod
        self.periodId = periodId
        self.eatenAt = eatenAt
        self.dishes = dishes
    }

    enum CodingKeys: String, CodingKey {
        case id
        case plannedFor = "planned_for"
        case mealPeriod = "meal_period"
        case periodId = "period_id"
        case eatenAt = "eaten_at"
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
    public var dishNames: [String]

    public init(
        ingredientId: String,
        ingredientName: String,
        neededQuantity: String,
        unit: String,
        isBought: Bool = false,
        dishNames: [String] = []
    ) {
        self.ingredientId = ingredientId
        self.ingredientName = ingredientName
        self.neededQuantity = neededQuantity
        self.unit = unit
        self.isBought = isBought
        self.dishNames = dishNames
    }

    enum CodingKeys: String, CodingKey {
        case ingredientId = "ingredient_id"
        case ingredientName = "ingredient_name"
        case neededQuantity = "needed_quantity"
        case unit
        case isBought = "is_bought"
        case dishNames = "dish_names"
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
