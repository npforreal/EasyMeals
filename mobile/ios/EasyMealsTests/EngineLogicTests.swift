import XCTest
@testable import EasyMealsCore

final class EngineLogicTests: XCTestCase {

    var cases: [[String: Any]] = []

    override func setUpWithError() throws {
        let bundle = Bundle.module
        guard let url = bundle.url(forResource: "engine_logic_cases", withExtension: "json", subdirectory: "Resources")
                ?? bundle.url(forResource: "engine_logic_cases", withExtension: "json") else {
            XCTFail("Không tìm thấy file engine_logic_cases.json trong test bundle")
            return
        }
        let data = try Data(contentsOf: url)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        cases = json["cases"] as! [[String: Any]]
    }

    private func norm(_ val: Any) -> String {
        return ExactDecimal(String(describing: val)).description
    }

    private func toRecipe(_ d: [String: Any]) -> Recipe {
        let ingList = (d["ingredients"] as! [[String: Any]]).map { i in
            RecipeIngredient(
                ingredientId: i["ingredient_id"] as! String,
                ingredientName: (i["name"] as? String) ?? (i["ingredient_name"] as? String) ?? "",
                quantity: String(describing: i["quantity"]!),
                unit: i["unit"] as! String
            )
        }
        return Recipe(
            id: d["id"] as! String,
            name: d["name"] as! String,
            category: d["category"] as! String,
            servings: (d["servings"] as? Int) ?? 4,
            instructions: [],
            ingredients: ingList
        )
    }

    private func toLots(_ arr: [[String: Any]]) -> [PantryLot] {
        return arr.map { item in
            let name = (item["name"] as? String) ?? (item["ingredient_name"] as? String) ?? ""
            let pur = (item["purchased"] != nil) ? String(describing: item["purchased"]!) : ((item["purchased_quantity"] != nil) ? String(describing: item["purchased_quantity"]!) : "0")
            let rem = (item["remaining"] != nil) ? String(describing: item["remaining"]!) : ((item["remaining_quantity"] != nil) ? String(describing: item["remaining_quantity"]!) : "0")
            let exp = item["expires_at"] as? String
            return PantryLot(
                id: item["id"] as! String,
                ingredientId: item["ingredient_id"] as! String,
                ingredientName: name,
                remainingQuantity: rem,
                purchasedQuantity: pur,
                unit: item["unit"] as! String,
                purchasedAt: "2025-12-01T00:00:00",
                expiresAt: exp,
                location: "fridge"
            )
        }
    }

    private func toConversions(_ raw: Any?) -> [Conversion]? {
        guard let list = raw as? [[String: Any]] else { return nil }
        return list.map { c in
            Conversion(
                fromIngredientId: c["from_ingredient_id"] as! String,
                toIngredientId: c["to_ingredient_id"] as! String,
                ratio: String(describing: c["ratio"]!),
                fromUnit: (c["from_unit"] as? String) ?? "g",
                toUnit: (c["to_unit"] as? String) ?? "g",
                note: c["note"] as? String
            )
        }
    }

    func testAllLogicCases() throws {
        for c in cases {
            let name = c["name"] as! String
            let op = c["op"] as! String
            let convs = toConversions(c["conversions"])
            let multiplier = (c["multiplier"] != nil) ? String(describing: c["multiplier"]!) : "1"

            switch op {
            case "check":
                let recipe = toRecipe(c["recipe"] as! [String: Any])
                let pantry = toLots(c["pantry"] as! [[String: Any]])
                let (canCook, deficits) = EasyMealsEngine.checkRecipeStock(
                    recipe: recipe,
                    pantryLots: pantry,
                    multiplier: multiplier,
                    conversions: convs
                )

                let exp = c["expect"] as! [String: Any]
                XCTAssertEqual(canCook, exp["can_cook"] as! Bool, "[\(name)] can_cook")
                let expDeficits = exp["deficits"] as! [String: Any]
                XCTAssertEqual(deficits.count, expDeficits.count, "[\(name)] deficits count")
                for (key, expVal) in expDeficits {
                    XCTAssertNotNil(deficits[key], "[\(name)] missing deficit for \(key)")
                    XCTAssertEqual(norm(deficits[key]!.missingQuantity), norm(expVal), "[\(name)] deficit amount for \(key)")
                }

            case "fifo":
                let recipe = toRecipe(c["recipe"] as! [String: Any])
                let pantry = toLots(c["pantry"] as! [[String: Any]])
                let (updatedLots, movements) = try EasyMealsEngine.deductRecipeStockFifo(
                    pantryLots: pantry,
                    recipe: recipe,
                    mealPlanId: "plan-1",
                    idempotencyKey: "key",
                    multiplier: multiplier,
                    conversions: convs
                )
                XCTAssertFalse(movements.isEmpty, "[\(name)] movements should not be empty")

                let exp = c["expect"] as! [String: Any]
                let expRemaining = exp["remaining"] as! [String: Any]
                var actualRemaining = Dictionary(uniqueKeysWithValues: pantry.map { ($0.id, norm($0.remainingQuantity)) })
                for u in updatedLots {
                    actualRemaining[u.id] = norm(u.remainingQuantity)
                }
                for (key, expVal) in expRemaining {
                    XCTAssertEqual(actualRemaining[key], norm(expVal), "[\(name)] lot \(key) remaining")
                }

            case "deduct_available":
                let recipe = toRecipe(c["recipe"] as! [String: Any])
                let pantry = toLots(c["pantry"] as! [[String: Any]])
                let outcome = try EasyMealsEngine.deductRecipeStockAvailable(
                    pantryLots: pantry,
                    recipe: recipe,
                    mealPlanId: "plan-1",
                    idempotencyKey: "key",
                    multiplier: multiplier,
                    conversions: convs
                )

                let exp = c["expect"] as! [String: Any]
                let expRemaining = exp["remaining"] as! [String: Any]
                var actualRemaining = Dictionary(uniqueKeysWithValues: pantry.map { ($0.id, norm($0.remainingQuantity)) })
                for u in outcome.updatedLots {
                    actualRemaining[u.id] = norm(u.remainingQuantity)
                }
                for (key, expVal) in expRemaining {
                    XCTAssertEqual(actualRemaining[key], norm(expVal), "[\(name)] lot \(key) remaining")
                }

                let expDeficits = exp["deficits"] as! [String: Any]
                XCTAssertEqual(outcome.deficits.count, expDeficits.count, "[\(name)] deficits count")
                for (key, expVal) in expDeficits {
                    XCTAssertNotNil(outcome.deficits[key], "[\(name)] missing deficit for \(key)")
                    XCTAssertEqual(norm(outcome.deficits[key]!.missingQuantity), norm(expVal), "[\(name)] deficit amount for \(key)")
                }

                let expMovements = exp["movements"] as! [String: Any]
                let actualMovements = Dictionary(uniqueKeysWithValues: outcome.movements.map { ($0.pantryLotId, norm($0.quantityDelta)) })
                for (key, expVal) in expMovements {
                    XCTAssertEqual(actualMovements[key], norm(expVal), "[\(name)] movement for \(key)")
                }

            case "undo":
                let pantry = toLots(c["pantry"] as! [[String: Any]])
                let rawMovements = c["movements"] as! [[String: Any]]
                let movements = rawMovements.map { m in
                    StockMovement(
                        id: m["id"] as! String,
                        pantryLotId: m["pantry_lot_id"] as! String,
                        quantityDelta: String(describing: m["delta"]!),
                        reason: m["reason"] as! String,
                        mealPlanId: m["meal_plan_id"] as? String,
                        idempotencyKey: m["idempotency_key"] as? String
                    )
                }

                let (restoredLots, _) = EasyMealsEngine.reverseStockMovements(
                    pantryLots: pantry,
                    movements: movements,
                    mealPlanId: c["meal_plan_id"] as! String
                )

                let exp = c["expect"] as! [String: Any]
                let expRemaining = exp["remaining"] as! [String: Any]
                var actualRemaining = Dictionary(uniqueKeysWithValues: pantry.map { ($0.id, norm($0.remainingQuantity)) })
                for u in restoredLots {
                    actualRemaining[u.id] = norm(u.remainingQuantity)
                }
                for (key, expVal) in expRemaining {
                    XCTAssertEqual(actualRemaining[key], norm(expVal), "[\(name)] lot \(key) remaining")
                }

            case "merge_plans":
                let toPlans = { (arr: Any) -> [MealPlan] in
                    (arr as! [[String: Any]]).map { p in
                        MealPlan(
                            id: p["id"] as! String,
                            plannedFor: p["planned_for"] as! String,
                            mealPeriod: p["meal_period"] as! String,
                            eatenAt: p["eaten_at"] as? String
                        )
                    }
                }
                let merged = EasyMealsEngine.mergeNewPlansIntoExisting(
                    toPlans(c["existing"]),
                    newPlans: toPlans(c["new_plans"]),
                    mode: (c["mode"] as? String) ?? "replace"
                )
                let expKept = (c["expect"] as! [String: Any])["kept_ids"] as! [String]
                let actualKept = merged.map(\.id)
                XCTAssertEqual(actualKept, expKept, "[\(name)] kept ids")

            case "shopping_budget":
                let itemsRaw = c["items"] as! [[String: Any]]
                let items = itemsRaw.map { it in
                    ShoppingItem(
                        ingredientId: it["ingredient_id"] as! String,
                        ingredientName: it["ingredient_name"] as! String,
                        neededQuantity: it["needed_quantity"] as! String,
                        unit: it["unit"] as! String,
                        isBought: (it["is_bought"] as? Bool) ?? false,
                        price: it["price"] as? String
                    )
                }
                let budget = EasyMealsEngine.calculateShoppingBudget(items)
                let exp = c["expect"] as! [String: Any]
                XCTAssertEqual(norm(budget.totalEstimatedBudget), norm(exp["total_estimated"] as! String), "[\(name)] total estimated")
                XCTAssertEqual(norm(budget.totalSpent), norm(exp["total_spent"] as! String), "[\(name)] total spent")
                XCTAssertEqual(budget.itemsWithPriceCount, exp["items_with_price_count"] as! Int, "[\(name)] items with price")
                XCTAssertEqual(budget.totalItemsCount, exp["total_items_count"] as! Int, "[\(name)] total items")

            case "plan", "plan_avoided":
                let rawRecipes = c["recipes"] as! [[String: Any]]
                let recipes = rawRecipes.map { toRecipe($0) }
                let pantry = toLots(c["pantry"] as! [[String: Any]])

                let startStr = c["start"] as! String
                let days = (c["days"] as? Int) ?? 1
                let formatter = DateFormatter()
                formatter.dateFormat = "yyyy-MM-dd"
                formatter.timeZone = TimeZone(secondsFromGMT: 0)
                let startDate = formatter.date(from: startStr)!
                let calendar = Calendar(identifier: .gregorian)
                let endDate = calendar.date(byAdding: .day, value: days - 1, to: startDate)!
                let endStr = formatter.string(from: endDate)
                let allowLeftovers = (c["allow_leftovers"] as? Bool) ?? true
                let leftoverDays = (c["leftover_days"] as? Int) ?? PlanLimits.leftoverDefaultDays
                let exp = c["expect"] as! [String: Any]

                if (exp["error"] as? Bool) == true {
                    XCTAssertThrowsError(
                        try EasyMealsEngine.generatePeriodPlan(
                            startDateStr: startStr,
                            endDateStr: endStr,
                            recipes: recipes,
                            currentPantryLots: pantry,
                            allowLeftovers: allowLeftovers,
                            conversions: convs,
                            leftoverDays: leftoverDays
                        ),
                        "[\(name)] Mong đợi lỗi vượt giới hạn số ngày nhưng không ném"
                    )
                    continue
                }

                let generated = try EasyMealsEngine.generatePeriodPlan(
                    startDateStr: startStr,
                    endDateStr: endStr,
                    recipes: recipes,
                    currentPantryLots: pantry,
                    allowLeftovers: allowLeftovers,
                    conversions: convs,
                    leftoverDays: leftoverDays,
                    avoidedIngredientIds: Set((c["avoided_ingredient_ids"] as? [String]) ?? [])
                )
                let plans = generated.meals
                let shopping = generated.shoppingList

                if op == "plan_avoided" {
                    let blocked = Set((c["avoided_ingredient_ids"] as? [String]) ?? [])
                    let recipesById = Dictionary(uniqueKeysWithValues: recipes.map { ($0.id, $0) })
                    XCTAssertFalse(plans.flatMap(\.dishes).contains { dish in
                        recipesById[dish.recipeId]?.ingredients.contains { blocked.contains($0.ingredientId) } ?? false
                    }, "[\(name)] no avoided ingredient in plan")
                    let excluded = recipes.filter { recipe in recipe.ingredients.contains { blocked.contains($0.ingredientId) } }
                    XCTAssertEqual(excluded.count, exp["excluded_recipe_count"] as? Int)
                    let excludedCategories = Set(excluded.map(\.category))
                    let warningCount = plans.filter { plan in
                        excludedCategories.contains { category in !plan.dishes.contains { $0.category == category } }
                    }.count
                    XCTAssertEqual(warningCount, exp["warning_count"] as? Int)
                    continue
                }

                let expDishes = exp["dishes"] as! [String]
                let actualDishes = plans.flatMap { $0.dishes }.map { $0.recipeName }
                XCTAssertEqual(actualDishes, expDishes, "[\(name)] dishes")

                let expShopping = exp["shopping"] as! [String: [String]]
                XCTAssertEqual(shopping.count, expShopping.count, "[\(name)] shopping count")
                for (key, expItem) in expShopping {
                    let actualItem = shopping.first { $0.ingredientId == key }
                    XCTAssertNotNil(actualItem, "[\(name)] shopping item \(key) missing")
                    if let actualItem = actualItem {
                        XCTAssertEqual(norm(actualItem.neededQuantity), norm(expItem[0]), "[\(name)] shopping qty for \(key)")
                        XCTAssertEqual(actualItem.unit, expItem[1], "[\(name)] shopping unit for \(key)")
                    }
                }

            default:
                XCTFail("[\(name)] op không hỗ trợ: \(op)")
            }
        }
    }
}
