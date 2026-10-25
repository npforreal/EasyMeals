import XCTest
@testable import EasyMealsCore

final class DateFormatterTests: XCTestCase {

    func testFormatDateVN() {
        XCTAssertEqual(AppDateFormatter.formatDateVN("2026-10-25"), "25/10/2026")
    }

    func testFormatRelativeDate() {
        var comps = DateComponents()
        comps.year = 2026
        comps.month = 10
        comps.day = 25
        let cal = Calendar.current
        let today = cal.date(from: comps)!

        XCTAssertEqual(AppDateFormatter.formatRelativeDate("2026-10-25", today: today), "Hôm nay, 25/10")
        XCTAssertEqual(AppDateFormatter.formatRelativeDate("2026-10-26", today: today), "Ngày mai, 26/10")
        XCTAssertEqual(AppDateFormatter.formatRelativeDate("2026-10-24", today: today), "Hôm qua, 24/10")
        // 2026-10-27 is Tuesday -> T3
        XCTAssertEqual(AppDateFormatter.formatRelativeDate("2026-10-27", today: today), "T3 27/10")
    }

    func testFormatExpiryStatus() {
        var comps = DateComponents()
        comps.year = 2026
        comps.month = 10
        comps.day = 25
        let cal = Calendar.current
        let today = cal.date(from: comps)!

        let exp0 = AppDateFormatter.formatExpiryStatus("2026-10-25", today: today)!
        XCTAssertTrue(exp0.isWarning)
        XCTAssertTrue(exp0.isExpired)

        let exp1 = AppDateFormatter.formatExpiryStatus("2026-10-26", today: today)!
        XCTAssertTrue(exp1.isWarning)
        XCTAssertFalse(exp1.isExpired)

        let exp2 = AppDateFormatter.formatExpiryStatus("2026-10-27", today: today)!
        XCTAssertTrue(exp2.isWarning)
        XCTAssertFalse(exp2.isExpired)

        let expSafe = AppDateFormatter.formatExpiryStatus("2026-10-30", today: today)!
        XCTAssertFalse(expSafe.isWarning)
        XCTAssertFalse(expSafe.isExpired)
    }
}
