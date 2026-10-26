import XCTest
@testable import EasyMealsCore

/** A4 - Vòng 13: hạn dùng mặc định theo nhóm nguyên liệu (khớp web & Android). */
final class ShoppingDefaultsTests: XCTestCase {

    func testExpiryDaysByCategory() {
        XCTAssertEqual(ShoppingDefaults.days(category: "thit"), 3)
        XCTAssertEqual(ShoppingDefaults.days(category: "gia_cam"), 2)
        XCTAssertEqual(ShoppingDefaults.days(category: "hai_san"), 2)
        XCTAssertEqual(ShoppingDefaults.days(category: "trung_sua"), 7)
        XCTAssertEqual(ShoppingDefaults.days(category: "rau_cu"), 5)
        XCTAssertEqual(ShoppingDefaults.days(category: "cu_qua"), 10)
        XCTAssertEqual(ShoppingDefaults.days(category: "gao_bot_mi"), 180)
        XCTAssertEqual(ShoppingDefaults.days(category: "gia_vi"), 180)
        XCTAssertEqual(ShoppingDefaults.days(category: "nuoc_cham_dau"), 180)
        XCTAssertEqual(ShoppingDefaults.days(category: "khac"), 7)
        XCTAssertEqual(ShoppingDefaults.days(category: "nhom-khong-tim-thay"), 7)
        XCTAssertEqual(ShoppingDefaults.days(category: nil), 7)
    }

    func testExpiryDateIsPurchasedDatePlusDays() {
        var components = DateComponents()
        components.calendar = Calendar.current
        components.year = 2026
        components.month = 10
        components.day = 25
        let bought = components.date!
        XCTAssertEqual(ShoppingDefaults.expiryDate(category: "thit", purchasedAt: bought), "2026-10-28")
        XCTAssertEqual(ShoppingDefaults.expiryDate(category: "hai_san", purchasedAt: bought), "2026-10-27")
        XCTAssertTrue(
            ShoppingDefaults.expiryDate(category: "nhom-khong-tim-thay", purchasedAt: bought).hasPrefix("2026-11-01"),
            "Nhóm lạ = 7 ngày: 25/10 + 7 = 01/11"
        )
    }
}
