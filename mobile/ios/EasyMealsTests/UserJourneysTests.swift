import XCTest
@testable import EasyMealsCore

final class UserJourneysTests: XCTestCase {

    var storage: AppStorage!

    override func setUp() {
        super.setUp()
        storage = AppStorage()
        storage.loadCatalogue()
        storage.pantryLots.removeAll()
        storage.mealPlans.removeAll()
        storage.shoppingItems.removeAll()
        storage.stockMovements.removeAll()
    }

    // Hành trình 1: Thêm đồ vào tủ (Pantry addition)
    func testJourney1_AddPantryLot() {
        XCTAssertFalse(storage.ingredients.isEmpty, "Danh mục nguyên liệu phải sẵn sàng")
        let firstIng = storage.ingredients[0]

        // Thêm một lô nguyên liệu vào tủ lạnh
        storage.addPantryLot(
            ingredientId: firstIng.id,
            ingredientName: firstIng.name,
            quantity: "500",
            unit: firstIng.defaultUnit,
            expiresAt: "2026-11-01"
        )

        XCTAssertEqual(storage.pantryLots.count, 1)
        XCTAssertEqual(storage.pantryLots[0].ingredientId, firstIng.id)
        XCTAssertEqual(storage.pantryLots[0].remainingQuantity, "500")
        XCTAssertEqual(storage.pantryLots[0].unit, firstIng.defaultUnit)

        // Cập nhật số lượng
        storage.updatePantryLotQuantity(id: storage.pantryLots[0].id, newQuantity: "400")
        XCTAssertEqual(storage.pantryLots[0].remainingQuantity, "400")

        // Xoá lô khỏi tủ
        storage.removePantryLot(id: storage.pantryLots[0].id)
        XCTAssertTrue(storage.pantryLots.isEmpty)
    }

    // Hành trình 2: Lập thực đơn -> Đã ăn -> Hoàn tác (Plan -> Eat -> Undo)
    func testJourney2_PlanEatUndo() throws {
        guard let thitLon = storage.ingredients.first(where: { $0.id == "thit_heo" }) ?? storage.ingredients.first else {
            XCTFail("Cần nguyên liệu thịt")
            return
        }

        // Tủ có 500g thịt
        storage.addPantryLot(
            ingredientId: thitLon.id,
            ingredientName: thitLon.name,
            quantity: "500",
            unit: "g"
        )

        // Chọn công thức đầu tiên
        let recipe = storage.recipes[0]
        let planId = "plan_test_journey_2"
        let plannedDish = PlannedDish(
            recipeId: recipe.id,
            recipeName: recipe.name,
            category: recipe.category,
            isLeftover: false,
            servings: recipe.servings
        )
        let plan = MealPlan(
            id: planId,
            plannedFor: "2026-10-25",
            mealPeriod: "lunch",
            dishes: [plannedDish]
        )
        storage.mealPlans.append(plan)

        // Ăn bữa (allowPartial = true để an toàn với mọi công thức)
        try storage.eatMeal(planId: planId, allowPartial: true)
        XCTAssertNotNil(storage.mealPlans[0].eatenAt, "Bữa ăn phải được đánh dấu đã ăn")
        XCTAssertNotNil(storage.undoMessage, "Phải có thông báo hoàn tác")

        // Hoàn tác
        storage.undoLastEatMeal()
        XCTAssertNil(storage.mealPlans[0].eatenAt, "Bữa ăn phải được huỷ đánh dấu đã ăn khi hoàn tác")
    }

    // Hành trình 3: Đi chợ -> Mua hàng -> Cho vào tủ (Shopping -> Pantry)
    func testJourney3_ShoppingToPantry() {
        // Thêm món cần mua
        storage.addCustomShoppingItem(name: "Trứng gà", quantity: "10", unit: "quả")
        storage.addCustomShoppingItem(name: "Rau muống", quantity: "1", unit: "bó")
        XCTAssertEqual(storage.shoppingItems.count, 2)

        // Đánh dấu đã mua 1 món
        let firstItemId = storage.shoppingItems[0].id
        storage.toggleShoppingItem(id: firstItemId)
        XCTAssertTrue(storage.shoppingItems[0].isBought)

        // Cho đồ đã mua vào tủ
        storage.bulkAddBoughtToPantry()

        // Món đã mua chuyển sang tủ lạnh
        XCTAssertEqual(storage.pantryLots.count, 1)
        XCTAssertEqual(storage.pantryLots[0].ingredientName, "Trứng gà")
        XCTAssertEqual(storage.pantryLots[0].remainingQuantity, "10")

        // Danh sách đi chợ chỉ còn lại món chưa mua
        XCTAssertEqual(storage.shoppingItems.count, 1)
        XCTAssertEqual(storage.shoppingItems[0].ingredientName, "Rau muống")
    }

    // Hành trình 4: Duyệt công thức -> Điều chỉnh khẩu phần -> Xem chế độ nấu
    func testJourney4_BrowseRecipesAndCookingMode() {
        XCTAssertEqual(storage.recipes.count, 133, "Phải có đúng 133 công thức")

        // Kiểm tra phân loại công thức
        let categories = Set(storage.recipes.map { $0.category })
        XCTAssertTrue(categories.contains("man") || categories.contains("canh") || categories.contains("rau"))

        // Chọn 1 công thức
        let recipe = storage.recipes[0]
        XCTAssertFalse(recipe.instructions.isEmpty, "Công thức phải có các bước thực hiện")
        XCTAssertFalse(recipe.ingredients.isEmpty, "Công thức phải có nguyên liệu")

        // Kiểm tra tính toán khẩu phần (scaling)
        let baseServings = ExactDecimal(recipe.servings)
        let targetServings = ExactDecimal("4")
        let multiplier = targetServings / baseServings

        for ing in recipe.ingredients {
            let scaledQty = ExactDecimal(ing.quantity) * multiplier
            XCTAssertGreaterThan(scaledQty, ExactDecimal(0), "Lượng nguyên liệu sau tỉ lệ phải > 0")
        }
    }

    // Kiểm tra tính năng gia hạn đồ tươi (+3 ngày)
    func testPantryLotExtendExpiry() {
        storage.addPantryLot(
            ingredientId: "rau_muong",
            ingredientName: "Rau muống",
            quantity: "1",
            unit: "bó",
            expiresAt: "2026-10-25"
        )
        let lotId = storage.pantryLots[0].id
        XCTAssertEqual(storage.pantryLots[0].expiresAt, "2026-10-25")

        // Gia hạn thêm 3 ngày
        storage.extendPantryLotExpiry(id: lotId, daysToAdd: 3)
        XCTAssertEqual(storage.pantryLots[0].expiresAt, "2026-10-28")
    }

    // Kiểm tra giới hạn thực đơn 1-7 ngày
    func testPlanDaysBoundariesAndCounts() throws {
        let start = "2026-10-25"

        // 1 ngày -> 2 bữa
        let (_, meals1, _) = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: start,
            endDateStr: start,
            recipes: storage.recipes,
            currentPantryLots: []
        )
        XCTAssertEqual(meals1.count, 2)

        // 3 ngày -> 6 bữa
        let (_, meals3, _) = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: start,
            endDateStr: "2026-10-27",
            recipes: storage.recipes,
            currentPantryLots: []
        )
        XCTAssertEqual(meals3.count, 6)

        // 7 ngày -> 14 bữa
        let (_, meals7, _) = try EasyMealsEngine.generatePeriodPlan(
            startDateStr: start,
            endDateStr: "2026-10-31",
            recipes: storage.recipes,
            currentPantryLots: []
        )
        XCTAssertEqual(meals7.count, 14)

        // 8 ngày -> Ném IncompatibleUnitError
        XCTAssertThrowsError(try EasyMealsEngine.generatePeriodPlan(
            startDateStr: start,
            endDateStr: "2026-11-01",
            recipes: storage.recipes,
            currentPantryLots: []
        ))
    }
}
