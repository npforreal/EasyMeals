import XCTest
@testable import EasyMealsCore

/**
 * A3 (Vòng 13): backup/state cũ vẫn giải mã được — migration tương thích.
 * Bài học từ lỗi iOS nuốt lỗi giải mã: bộ giải mã KHÔNG được văng lỗi trên
 * bản dữ liệu cũ thiếu khoá mới; thiếu khoá phải về giá trị mặc định tường minh.
 */
final class BackupMigrationTests: XCTestCase {

    func testLegacyBackupWithoutShoppingItemsDecodes() throws {
        let legacy = """
        {
          "app_version": "2.0.0",
          "exported_at": "2026-10-25T00:00:00Z",
          "pantry_lots": [],
          "meal_plans": [],
          "stock_movements": []
        }
        """.data(using: .utf8)!

        let payload = try BackupManager.validateAndDecode(jsonData: legacy)
        XCTAssertEqual(payload.pantryLots.count, 0)
        XCTAssertEqual(payload.shoppingItems.count, 0, "Bản cũ thiếu.shopping_items về rỗng, không văng lỗi")
    }

    func testLegacyBackupWithShoppingItemsButNoSourceFlag() throws {
        let legacy = """
        {
          "app_version": "2.0.0",
          "exported_at": "2026-10-25T00:00:00Z",
          "pantry_lots": [],
          "meal_plans": [],
          "stock_movements": [],
          "shopping_items": [
            {
              "ingredient_id": "ing-9",
              "ingredient_name": "Nước mắm",
              "needed_quantity": "500",
              "unit": "ml",
              "is_bought": true,
              "dish_names": ["Món cũ"]
            }
          ]
        }
        """.data(using: .utf8)!

        let payload = try BackupManager.validateAndDecode(jsonData: legacy)
        XCTAssertEqual(payload.shoppingItems.count, 1)
        let item = payload.shoppingItems[0]
        XCTAssertEqual(item.ingredientId, "ing-9")
        XCTAssertTrue(item.isBought)
        // Bản cũ không có trường nguồn phát sinh -> coi như mục sinh tự (không phải tự thêm).
        XCTAssertFalse(item.isManuallyAdded)
        XCTAssertEqual(item.id, "ing-9_ml")
    }

    func testShoppingItemWithoutSourceFlagVsManual() throws {
        let noFlag = try JSONDecoder().decode(ShoppingItem.self, from: """
        {"ingredient_id": "i", "ingredient_name": "X", "needed_quantity": "1", "unit": "g"}
        """.data(using: .utf8)!)
        XCTAssertFalse(noFlag.isManuallyAdded)

        let manual = try JSONDecoder().decode(ShoppingItem.self, from: """
        {"ingredient_id": "i", "ingredient_name": "X", "needed_quantity": "1", "unit": "g", "is_manually_added": true}
        """.data(using: .utf8)!)
        XCTAssertTrue(manual.isManuallyAdded)
        XCTAssertEqual(manual.id, "i_g")
    }
}
