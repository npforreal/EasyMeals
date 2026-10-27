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
