import XCTest
@testable import EasyMealsCore

final class CatalogueLoadingTests: XCTestCase {
    func testLoadBundledCatalogue() throws {
        let bundle = CatalogueLoader.shared.loadBundledCatalogue()
        XCTAssertNotNil(bundle, "CatalogueBundle không được nil khi nạp từ asset thật")
        guard let bundle = bundle else { return }

        XCTAssertEqual(bundle.recipes.count, 133, "Số lượng món ăn phải là 133")
        XCTAssertGreaterThanOrEqual(bundle.ingredients.count, 147, "Số lượng nguyên liệu phải >= 147")
        XCTAssertFalse(bundle.version.isEmpty, "Catalogue version không được rỗng")

        for ing in bundle.ingredients {
            XCTAssertFalse(ing.id.isEmpty, "Ingredient ID không được rỗng")
            XCTAssertFalse(ing.name.isEmpty, "Ingredient name không được rỗng")
            XCTAssertFalse(ing.defaultUnit.isEmpty, "Ingredient defaultUnit không được rỗng: \(ing.name)")
        }
    }

    func testConversionsNotEmptyAfterCatalogueLoad() throws {
        let bundle = CatalogueLoader.shared.loadBundledCatalogue()
        XCTAssertNotNil(bundle)
        guard let bundle = bundle else { return }
        XCTAssertFalse(bundle.conversions.isEmpty, "Conversions không được rỗng sau khi nạp catalogue thật")
    }

    func testGetTotalIngredientStock_GaoToComNong() throws {
        let bundle = CatalogueLoader.shared.loadBundledCatalogue()
        XCTAssertNotNil(bundle)
        guard let bundle = bundle else { return }

        let idGao = "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b"
        let idComNong = "412a8c08-4863-5000-aedd-13e2ba3adb69"

        let lot = PantryLot(
            id: "test-lot-gao-1",
            ingredientId: idGao,
            ingredientName: "Gạo",
            remainingQuantity: "500",
            purchasedQuantity: "500",
            unit: "g",
            purchasedAt: "2026-01-01",
            expiresAt: nil
        )

        let total = EasyMealsEngine.getTotalIngredientStock(
            pantryLots: [lot],
            ingredientId: idComNong,
            targetUnit: "g",
            conversions: bundle.conversions
        )
        XCTAssertEqual(total.description, "1250", "500g gạo phải quy đổi thành 1250g cơm nóng (ratio 2.5)")
    }
}
