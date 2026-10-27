import Foundation

/// F2 - Vòng 13: nội dung nhắc việc cục bộ (không gọi mạng, không gửi dữ liệu đi).
///
/// Chỉ dùng dữ liệu đang có trên máy:
/// - Lô sắp hết hạn / đã quá hạn nhưng còn hàng trong tủ.
/// - Bữa ăn trong ngày chưa đánh dấu "Đã ăn" (gợi ý chuẩn bị trước).
///
/// Không có dữ liệu rã đông riêng, nên phần "chuẩn bị" chỉ là lời nhắc chung cho bữa
/// trong ngày, không suy diễn thời gian rã đông.
public struct ReminderDigest: Equatable, Sendable {
    public let title: String
    public let body: String

    public init(title: String, body: String) {
        self.title = title
        self.body = body
    }
}

public enum ReminderPlanner {

    /// Giờ nhắc cố định theo múi giờ của thiết bị.
    public static let reminderHour = 9
    /// Số ngày nhắc trước hạn dùng.
    public static let expiryWindowDays = 2

    private static let maxExpiryLines = 3
    private static let maxMealLines = 2

    private static func dayOnly(_ value: String?) -> String? {
        guard let value, value.count >= 10 else { return nil }
        let prefix = String(value.prefix(10))
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = "yyyy-MM-dd"
        guard formatter.date(from: prefix) != nil else { return nil }
        return prefix
    }

    private static func periodLabel(_ period: String) -> String {
        switch period {
        case "breakfast": return "Sáng"
        case "lunch": return "Trưa"
        case "dinner": return "Tối"
        default: return period
        }
    }

    private static func periodOrder(_ period: String) -> Int {
        switch period {
        case "breakfast": return 0
        case "lunch": return 1
        case "dinner": return 2
        default: return 3
        }
    }

    /// "2026-10-27" -> "27/10/2026"; giá trị lạ được giữ nguyên.
    public static func formatDay(_ value: String) -> String {
        guard value.count >= 10 else { return value }
        let parts = value.prefix(10).split(separator: "-")
        guard parts.count == 3 else { return value }
        return "\(parts[2])/\(parts[1])/\(parts[0])"
    }

    /// Cộng/trừ ngày trên chuỗi "yyyy-MM-dd" theo lịch Gregorian (UTC để không lệch múi giờ).
    private static func addDays(_ day: String, _ days: Int) -> String? {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = "yyyy-MM-dd"
        guard let date = formatter.date(from: day) else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC") ?? .current
        guard let shifted = calendar.date(byAdding: .day, value: days, to: date) else { return nil }
        return formatter.string(from: shifted)
    }

    /// Tạo nội dung nhắc cho một ngày. Trả về `nil` khi không có gì cần nhắc.
    public static func buildDigest(
        pantryLots: [PantryLot],
        mealPlans: [MealPlan],
        day: String,
        expiryWindowDays: Int = ReminderPlanner.expiryWindowDays
    ) -> ReminderDigest? {
        guard let today = dayOnly(day) else { return nil }
        let window = expiryWindowDays >= 0 ? expiryWindowDays : ReminderPlanner.expiryWindowDays
        let limit = addDays(today, window) ?? today
        var lines: [String] = []

        let expiring = pantryLots.compactMap { lot -> (PantryLot, String, Bool)? in
            guard let expiry = dayOnly(lot.expiresAt), expiry <= limit else { return nil }
            guard (Double(lot.remainingQuantity) ?? 0) > 0 else { return nil }
            return (lot, expiry, expiry < today)
        }
        .sorted { $0.1 < $1.1 }
        .prefix(maxExpiryLines)

        for (lot, expiry, overdue) in expiring {
            let name = lot.ingredientName.isEmpty ? lot.ingredientId : lot.ingredientName
            let prefix = overdue ? "Đã quá hạn" : "Sắp hết hạn"
            lines.append("\(prefix): \(name) (\(lot.remainingQuantity) \(lot.unit), hạn \(formatDay(expiry)))")
        }

        let meals = mealPlans
            .filter { ($0.eatenAt ?? "").isEmpty }
            .filter { String($0.plannedFor.prefix(10)) == today }
            .sorted { periodOrder($0.mealPeriod) < periodOrder($1.mealPeriod) }
            .prefix(maxMealLines)

        for plan in meals {
            let dishNames = plan.dishes
                .filter { !$0.isLeftover }
                .map { $0.recipeName.isEmpty ? $0.recipeId : $0.recipeName }
                .filter { !$0.isEmpty }
            if dishNames.isEmpty { continue }
            lines.append("Hôm nay · \(periodLabel(plan.mealPeriod)): \(dishNames.joined(separator: ", "))")
        }

        guard !lines.isEmpty else { return nil }
        return ReminderDigest(
            title: "EasyMeals · nhắc việc hôm nay",
            body: lines.joined(separator: "\n")
        )
    }

    /// Mốc 09:00 theo múi giờ thiết bị cho `days` ngày kế tiếp (bắt đầu hôm nay nếu còn kịp).
    /// Dùng Calendar nên tự đúng khi đổi múi giờ hoặc chuyển DST.
    public static func upcomingTriggerDates(
        from now: Date = Date(),
        days: Int = 7,
        hour: Int = ReminderPlanner.reminderHour,
        calendar: Calendar = .current
    ) -> [Date] {
        let count = max(0, days)
        guard count > 0 else { return [] }
        let safeHour = min(max(hour, 0), 23)
        var results: [Date] = []
        var cursor = now
        for _ in 0..<count {
            guard let candidate = calendar.date(
                bySettingHour: safeHour,
                minute: 0,
                second: 0,
                of: cursor
            ) else { break }
            let start = candidate > cursor ? candidate : (calendar.date(byAdding: .day, value: 1, to: candidate) ?? candidate)
            results.append(start)
            cursor = start
        }
        return results
    }

    /// "yyyy-MM-dd" theo múi giờ thiết bị.
    public static func dayString(_ date: Date, calendar: Calendar = .current) -> String {
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
}
