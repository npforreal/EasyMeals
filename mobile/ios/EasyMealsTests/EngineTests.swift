import XCTest
@testable import EasyMealsCore

final class EngineTests: XCTestCase {

    var fixtureData: Data!
    var fixtureJSON: [String: Any]!

    override func setUpWithError() throws {
        let bundle = Bundle.module
        guard let url = bundle.url(forResource: "engine_test_cases", withExtension: "json", subdirectory: "Resources")
                ?? bundle.url(forResource: "engine_test_cases", withExtension: "json") else {
            XCTFail("Không tìm thấy file engine_test_cases.json trong test bundle")
            return
        }
        fixtureData = try Data(contentsOf: url)
        fixtureJSON = try JSONSerialization.jsonObject(with: fixtureData) as? [String: Any]
    }

    func testUnitConversions() throws {
        guard let items = fixtureJSON["unit_conversions"] as? [[String: Any]] else {
            XCTFail("Thiếu unit_conversions")
            return
        }

        for item in items {
            let qty = String(describing: item["quantity"]!)
            let fromUnit = item["from_unit"] as! String
            let toUnit = item["to_unit"] as! String
            let expected = item["expected"] as! String

            let res = try UnitDimensions.convert(quantity: ExactDecimal(qty), from: fromUnit, to: toUnit)
            XCTAssertEqual(res.description, expected, "Chuyển đổi \(qty) \(fromUnit) -> \(toUnit) phải bằng \(expected)")
        }
    }

    func testSharedPlannerPreferenceFixture() throws {
        let fixtureURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("../../tests/fixtures/planner_preferences.json")
        let data = try JSONSerialization.jsonObject(with: Data(contentsOf: fixtureURL)) as! [String: Any]
        let recipesData = try JSONSerialization.data(withJSONObject: data["recipes"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: data["pantry"]!)
        let recipes = try JSONDecoder().decode([Recipe].self, from: recipesData)
        let pantry = try JSONDecoder().decode([PantryLot].self, from: pantryData)
        let date = data["reference_date"] as! String
        let result = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: date,
            endDateStr: date,
            recipes: recipes,
            currentPantryLots: pantry,
            allowLeftovers: false,
            householdSettings: HouseholdSettings(mealPeriods: ["lunch"])
        )
        let selected = try XCTUnwrap(result.meals.first?.dishes.first(where: { $0.category == "man" }))
        XCTAssertEqual(selected.recipeId, data["expected_recipe_id"] as? String)
        XCTAssertEqual(selected.selectionReason, data["expected_reason"] as? String)
        let recency = data["recency_case"] as! [String: Any]
        let recentIds = Set(recency["recently_cooked_recipe_ids"] as! [String])
        let variedResult = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: date,
            endDateStr: date,
            recipes: recipes,
            currentPantryLots: pantry,
            allowLeftovers: false,
            householdSettings: HouseholdSettings(mealPeriods: ["lunch"]),
            recentlyCookedRecipeIds: recentIds
        )
        let varied = try XCTUnwrap(variedResult.meals.first?.dishes.first(where: { $0.category == "man" }))
        XCTAssertEqual(varied.recipeId, recency["expected_recipe_id"] as? String)
        XCTAssertEqual(varied.selectionReason, recency["expected_reason"] as? String)
    }

    func testFifoStockDeduction() throws {
        guard let fifoDict = fixtureJSON["fifo_deduction"] as? [String: Any] else {
            XCTFail("Thiếu fifo_deduction")
            return
        }

        let recipeData = try JSONSerialization.data(withJSONObject: fifoDict["recipe"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: fifoDict["pantry"]!)

        let recipe = try JSONDecoder().decode(Recipe.self, from: recipeData)
        let pantryLots = try JSONDecoder().decode([PantryLot].self, from: pantryData)

        let (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe: recipe, pantryLots: pantryLots)
        let checkExp = fifoDict["check_stock_expected"] as! [String: Any]
        XCTAssertEqual(canCook, checkExp["can_cook"] as! Bool)
        XCTAssertEqual(deficits.count, checkExp["deficits_count"] as! Int)

        let (updatedLots, movements) = try EasyMealsEngine.deductRecipeStockFifo(
            pantryLots: pantryLots,
            recipe: recipe,
            mealPlanId: "bbbbbbbb-0001-0000-0000-000000000001",
            idempotencyKey: "fifo_test"
        )

        let dedExp = fifoDict["deduction_expected"] as! [String: Any]
        let expLots = dedExp["updated_lots"] as! [[String: Any]]
        XCTAssertEqual(updatedLots.count, expLots.count)

        for i in 0..<updatedLots.count {
            XCTAssertEqual(updatedLots[i].id, expLots[i]["id"] as! String)
            XCTAssertEqual(updatedLots[i].remainingQuantity, String(describing: expLots[i]["remaining_quantity"]!))
        }

        let expMovs = dedExp["movements"] as! [[String: Any]]
        XCTAssertEqual(movements.count, expMovs.count)
        for i in 0..<movements.count {
            XCTAssertEqual(movements[i].pantryLotId, expMovs[i]["pantry_lot_id"] as! String)
            XCTAssertEqual(movements[i].quantityDelta, String(describing: expMovs[i]["quantity_delta"]!))
            XCTAssertEqual(movements[i].reason, expMovs[i]["reason"] as! String)
        }
    }

    func testUndoConsumption() throws {
        guard let fifoDict = fixtureJSON["fifo_deduction"] as? [String: Any],
              let undoDict = fixtureJSON["undo_consumption"] as? [String: Any] else {
            XCTFail("Thiếu dữ liệu undo")
            return
        }

        let recipeData = try JSONSerialization.data(withJSONObject: fifoDict["recipe"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: fifoDict["pantry"]!)
        let recipe = try JSONDecoder().decode(Recipe.self, from: recipeData)
        let pantryLots = try JSONDecoder().decode([PantryLot].self, from: pantryData)

        let (updatedLots, movements) = try EasyMealsEngine.deductRecipeStockFifo(
            pantryLots: pantryLots,
            recipe: recipe,
            mealPlanId: "bbbbbbbb-0001-0000-0000-000000000001",
            idempotencyKey: "fifo_test"
        )

        let (restoredLots, _) = EasyMealsEngine.reverseStockMovements(
            pantryLots: updatedLots,
            movements: movements,
            mealPlanId: "bbbbbbbb-0001-0000-0000-000000000001"
        )

        let expRestored = undoDict["restored_lots"] as! [[String: Any]]
        XCTAssertEqual(restoredLots.count, expRestored.count)
        for i in 0..<restoredLots.count {
            XCTAssertEqual(restoredLots[i].id, expRestored[i]["id"] as! String)
            XCTAssertEqual(restoredLots[i].remainingQuantity, String(describing: expRestored[i]["remaining_quantity"]!))
        }
    }

    func testMealPlannerGeneration() throws {
        guard let planData = fixtureJSON["planner_generation"] as? [String: Any] else {
            XCTFail("Thiếu planner_generation")
            return
        }

        let recipesData = try JSONSerialization.data(withJSONObject: planData["recipes"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: planData["pantry"]!)
        let recipes = try JSONDecoder().decode([Recipe].self, from: recipesData)
        let pantryLots = try JSONDecoder().decode([PantryLot].self, from: pantryData)

        let startDate = planData["start_date"] as! String
        let endDate = planData["end_date"] as! String

        let result = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: startDate,
            endDateStr: endDate,
            recipes: recipes,
            currentPantryLots: pantryLots,
            allowLeftovers: true
        )

        let expMealsCount = planData["expected_meals_count"] as! Int
        XCTAssertEqual(result.meals.count, expMealsCount)

        let expDishesPerMeal = planData["expected_dishes_per_meal"] as! [[[String: Any]]]
        for m in 0..<result.meals.count {
            let actualDishes = result.meals[m].dishes
            let expDishes = expDishesPerMeal[m]
            XCTAssertEqual(actualDishes.count, expDishes.count)

            for d in 0..<actualDishes.count {
                XCTAssertEqual(actualDishes[d].recipeName, expDishes[d]["recipe_name"] as! String)
                XCTAssertEqual(actualDishes[d].category, expDishes[d]["category"] as! String)
                XCTAssertEqual(actualDishes[d].isLeftover, expDishes[d]["is_leftover"] as! Bool)
            }
        }

        // Kiểm tra danh sách đi chợ
        var sortedActual = result.shoppingList
        sortedActual.sort { $0.ingredientId < $1.ingredientId }
        let expShopping = planData["expected_shopping_items"] as! [[String: Any]]
        XCTAssertEqual(sortedActual.count, expShopping.count)

        for s in 0..<sortedActual.count {
            XCTAssertEqual(sortedActual[s].ingredientId, expShopping[s]["ingredient_id"] as! String)
            XCTAssertEqual(sortedActual[s].neededQuantity, String(describing: expShopping[s]["needed_quantity"]!))
            XCTAssertEqual(sortedActual[s].unit, expShopping[s]["unit"] as! String)
        }
    }

    func testFifoSameExpiryTiebreak() throws {
        guard let tieData = fixtureJSON["fifo_deduction_same_expiry_tiebreak"] as? [String: Any] else {
            XCTFail("Thiếu fifo_deduction_same_expiry_tiebreak")
            return
        }

        let recipeData = try JSONSerialization.data(withJSONObject: tieData["recipe"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: tieData["pantry"]!)
        let recipe = try JSONDecoder().decode(Recipe.self, from: recipeData)
        let pantryLots = try JSONDecoder().decode([PantryLot].self, from: pantryData)

        let (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe: recipe, pantryLots: pantryLots)
        let checkExp = tieData["check_stock_expected"] as! [String: Any]
        XCTAssertEqual(canCook, checkExp["can_cook"] as! Bool)
        XCTAssertEqual(deficits.count, checkExp["deficits_count"] as! Int)

        let (updatedLots, movements) = try EasyMealsEngine.deductRecipeStockFifo(
            pantryLots: pantryLots,
            recipe: recipe,
            mealPlanId: "bbbbbbbb-0001-0000-000000000010",
            idempotencyKey: "tiebreak_test"
        )

        let dedExp = tieData["deduction_expected"] as! [String: Any]
        let expLots = dedExp["updated_lots"] as! [[String: Any]]
        XCTAssertEqual(updatedLots.count, expLots.count)
        XCTAssertEqual(updatedLots[0].id, expLots[0]["id"] as! String)
        XCTAssertEqual(updatedLots[0].remainingQuantity, String(describing: expLots[0]["remaining_quantity"]!))
        XCTAssertEqual(updatedLots[1].id, expLots[1]["id"] as! String)
        XCTAssertEqual(updatedLots[1].remainingQuantity, String(describing: expLots[1]["remaining_quantity"]!))

        let expMovs = dedExp["movements"] as! [[String: Any]]
        XCTAssertEqual(movements.count, expMovs.count)
        for i in 0..<movements.count {
            XCTAssertEqual(movements[i].pantryLotId, expMovs[i]["pantry_lot_id"] as! String)
            XCTAssertEqual(movements[i].quantityDelta, String(describing: expMovs[i]["quantity_delta"]!))
            XCTAssertEqual(movements[i].reason, expMovs[i]["reason"] as! String)
        }
    }

    func testStockInsufficient() throws {
        guard let insuff = fixtureJSON["stock_insufficient"] as? [String: Any] else {
            XCTFail("Thiếu stock_insufficient")
            return
        }

        let recipeData = try JSONSerialization.data(withJSONObject: insuff["recipe"]!)
        let pantryData = try JSONSerialization.data(withJSONObject: insuff["pantry"]!)
        let recipe = try JSONDecoder().decode(Recipe.self, from: recipeData)
        let pantryLots = try JSONDecoder().decode([PantryLot].self, from: pantryData)

        let (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe: recipe, pantryLots: pantryLots)
        let checkExp = insuff["check_stock_expected"] as! [String: Any]
        XCTAssertEqual(canCook, checkExp["can_cook"] as! Bool)
        XCTAssertEqual(deficits.count, checkExp["deficits_count"] as! Int)

        XCTAssertThrowsError(
            try EasyMealsEngine.deductRecipeStockFifo(
                pantryLots: pantryLots,
                recipe: recipe,
                mealPlanId: "bbbbbbbb-0001-0000-000000000011",
                idempotencyKey: "insuff_test"
            )
        ) { error in
            XCTAssertTrue(error is InsufficientStockError)
        }
    }

    func testIncompatibleUnitThrows() {
        XCTAssertThrowsError(try UnitDimensions.convert(quantity: ExactDecimal("100"), from: "g", to: "ml")) { error in
            XCTAssertTrue(error is IncompatibleUnitError)
        }
    }
}
