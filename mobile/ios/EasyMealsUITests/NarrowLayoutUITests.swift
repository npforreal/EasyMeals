import XCTest

/// D2b: kiểm tra giao diện iOS thật trên simulator (khổ hẹp: iPhone SE).
final class NarrowLayoutUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    func testRecipesTabShowsAvoidIngredientFilterAndWarning() {
        let app = XCUIApplication()
        app.launch()
        app.tabBars.buttons["Công thức"].tap()
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Nguyên liệu cần tránh'")).firstMatch.waitForExistence(timeout: 5))
    }

    func testTodayTabShowsPlanControls() {
        let app = XCUIApplication()
        app.launch()
        app.tabBars.buttons["Hôm nay"].tap()
        XCTAssertTrue(app.staticTexts.firstMatch.waitForExistence(timeout: 5))
    }
}

/// D2b: chọn món thủ công chứa nguyên liệu cần tránh phải hỏi xác nhận; "Huỷ" thì không thêm.
final class AvoidIngredientConfirmationUITests: XCTestCase {
    // "Rau om" chỉ có trong món "Canh khoai mỡ nấu tôm thịt" (tra từ data/catalogue.json).
    private let avoidedIngredientId = "3e49235f-ec85-5dc4-9876-edeadec74f8b"
    private let recipeName = "Canh khoai mỡ nấu tôm thịt"

    override func setUp() { continueAfterFailure = false }

    private func launchWithPlan() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments += ["-easymeals.recipe.avoidedIngredientIds", avoidedIngredientId]
        app.launch()
        app.tabBars.buttons["Hôm nay"].tap()
        let addButton = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Thêm món'")).firstMatch
        if !addButton.waitForExistence(timeout: 3) {
            let generate = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Lên thực đơn'")).firstMatch
            XCTAssertTrue(generate.waitForExistence(timeout: 5))
            generate.tap()
        }
        XCTAssertTrue(addButton.waitForExistence(timeout: 10), "Không có bữa chưa ăn để thêm món")
        return app
    }

    private func openPickerAndChooseViolatingRecipe(_ app: XCUIApplication) {
        app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Thêm món'")).firstMatch.tap()
        let search = app.searchFields.firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 5))
        search.tap()
        search.typeText("khoai")
        let row = app.buttons["recipe-picker-000888e7-88de-5217-a3c2-78659d24b88c"]
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Chứa nguyên liệu bạn cần tránh"].exists)
        row.tap()
    }

    func testViolatingRecipeAsksConfirmationAndCancelDoesNotAdd() {
        let app = launchWithPlan()
        openPickerAndChooseViolatingRecipe(app)
        XCTAssertTrue(app.alerts.staticTexts.matching(NSPredicate(format: "label CONTAINS 'mà bạn đã đặt cần tránh'")).firstMatch.waitForExistence(timeout: 5))
        app.alerts.buttons["Huỷ"].tap()
        // Vẫn ở màn chọn món, món chưa được thêm vào thực đơn.
        XCTAssertTrue(app.searchFields.firstMatch.waitForExistence(timeout: 3))
        XCTAssertFalse(app.alerts.firstMatch.exists)
    }

    func testConfirmAddsViolatingRecipeToMeal() {
        let app = launchWithPlan()
        openPickerAndChooseViolatingRecipe(app)
        let confirm = app.alerts.buttons["Vẫn thêm"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 5))
        confirm.tap()
        XCTAssertTrue(app.staticTexts[recipeName].waitForExistence(timeout: 5), "Món chưa xuất hiện trong thực đơn sau khi xác nhận")
    }
}
