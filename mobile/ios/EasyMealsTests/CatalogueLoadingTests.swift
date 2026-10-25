import XCTest
@testable import EasyMealsCore

final class CatalogueLoadingTests: XCTestCase {
    func testLoadBundledCatalogue() throws {
        let bundle = CatalogueLoader.shared.loadBundledCatalogue()
        XCTAssertNotNil(bundle, "CatalogueBundle không được nil khi nạp từ asset thật")
        guard let bundle = bundle else { return }

        XCTAssertEqual(bundle.recipes.count, 133, "Số lượng món ăn phải là 133")
        XCTAssertEqual(bundle.ingredients.count, 147, "Số lượng nguyên liệu phải là 147")
        XCTAssertFalse(bundle.version.isEmpty, "Catalogue version không được rỗng")

        for ing in bundle.ingredients {
            XCTAssertFalse(ing.id.isEmpty, "Ingredient ID không được rỗng")
            XCTAssertFalse(ing.name.isEmpty, "Ingredient name không được rỗng")
            XCTAssertFalse(ing.defaultUnit.isEmpty, "Ingredient defaultUnit không được rỗng: \(ing.name)")
        }
    }
}
