import XCTest
@testable import EasyMealsCore

/// F2 - Vòng 13: nội dung nhắc việc và mốc 09:00 theo múi giờ thiết bị.
final class ReminderPlannerTests: XCTestCase {

    private var calendar: Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Ho_Chi_Minh")!
        return cal
    }

    private func date(_ text: String) -> Date {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "Asia/Ho_Chi_Minh")
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.date(from: text)!
    }

    private func lot(
        _ id: String,
        name: String = "Sữa",
        remaining: String = "1",
        unit: String = "l",
        expiry: String?
    ) -> PantryLot {
        PantryLot(
            id: id,
            ingredientId: "ing-\(id)",
            ingredientName: name,
            remainingQuantity: remaining,
            purchasedQuantity: "1",
            unit: unit,
            purchasedAt: "2026-10-25",
            expiresAt: expiry
        )
    }

    private func plan(
        _ id: String,
        plannedFor: String = "2026-10-27",
        period: String = "lunch",
        eatenAt: String? = nil,
        dishNames: [String] = ["Thịt kho"]
    ) -> MealPlan {
        MealPlan(
            id: id,
            plannedFor: plannedFor,
            mealPeriod: period,
            eatenAt: eatenAt,
            dishes: dishNames.enumerated().map { index, name in
                PlannedDish(
                    id: "\(id)-\(index)",
                    recipeId: "r-\(index)",
                    recipeName: name,
                    category: "man",
                    isLeftover: false,
                    servings: 2
                )
            }
        )
    }

    func testUpcomingTriggersAreNineLocalAndConsecutive() {
        let now = date("2026-10-27 07:30")
        let triggers = ReminderPlanner.upcomingTriggerDates(from: now, days: 3, calendar: calendar)
        XCTAssertEqual(triggers.count, 3)

        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        XCTAssertEqual(formatter.string(from: triggers[0]), "2026-10-27 09:00")
        XCTAssertEqual(formatter.string(from: triggers[1]), "2026-10-28 09:00")
        XCTAssertEqual(formatter.string(from: triggers[2]), "2026-10-29 09:00")
    }

    func testTriggerSkipsToTomorrowWhenNinePassed() {
        let now = date("2026-10-27 09:00")
        let triggers = ReminderPlanner.upcomingTriggerDates(from: now, days: 1, calendar: calendar)
        XCTAssertEqual(triggers.count, 1)
        XCTAssertEqual(ReminderPlanner.dayString(triggers[0], calendar: calendar), "2026-10-28")
    }

    func testDigestListsExpiringLotsAndTodaysMeals() {
        let lots = [
            lot("l1", name: "Sữa", expiry: "2026-10-27"),
            lot("l2", name: "Rau muống", expiry: "2026-10-26"),
            lot("l3", name: "Gạo", unit: "kg", expiry: "2026-12-01"),
        ]
        let plans = [
            plan("p1", period: "dinner", dishNames: ["Canh chua"]),
            plan("p2", period: "lunch", dishNames: ["Thịt kho", "Rau luộc"]),
            plan("p3", plannedFor: "2026-10-28"),
        ]

        let digest = ReminderPlanner.buildDigest(pantryLots: lots, mealPlans: plans, day: "2026-10-27")
        XCTAssertNotNil(digest)
        let body = digest!.body
        XCTAssertTrue(body.contains("Sữa"))
        XCTAssertTrue(body.contains("Đã quá hạn"))
        XCTAssertTrue(body.contains("Rau muống"))
        XCTAssertFalse(body.contains("Gạo"), "lô còn xa hạn không được nhắc")
        XCTAssertTrue(body.contains("Trưa: Thịt kho, Rau luộc"))
        XCTAssertTrue(body.contains("Tối: Canh chua"))
        XCTAssertFalse(body.contains("2026-10-28"), "không nhắc bữa của ngày khác")
    }

    func testDigestSkipsEatenMealsAndEmptyLots() {
        let lots = [lot("l1", remaining: "0", expiry: "2026-10-26")]
        let plans = [plan("p1", eatenAt: "2026-10-27T12:00:00Z")]
        XCTAssertNil(ReminderPlanner.buildDigest(pantryLots: lots, mealPlans: plans, day: "2026-10-27"))
    }

    func testDigestIsNilWhenNothingToRemind() {
        XCTAssertNil(ReminderPlanner.buildDigest(pantryLots: [], mealPlans: [], day: "2026-10-27"))
    }

    func testFormatDayUsesVietnameseOrder() {
        XCTAssertEqual(ReminderPlanner.formatDay("2026-10-27"), "27/10/2026")
    }
}
