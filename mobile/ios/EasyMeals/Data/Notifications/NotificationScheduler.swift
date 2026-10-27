import Foundation
import UserNotifications

/// F2 - Vòng 13: lên lịch thông báo cục bộ trên iOS.
///
/// iOS không chạy mã ứng dụng lúc gửi thông báo, nên nội dung được tính sẵn cho 7 ngày
/// kế tiếp mỗi lần người dùng bật nhắc việc hoặc mở lại Cài đặt. Không có mạng, không
/// có push server; quyền thông báo chỉ được xin khi người dùng bật.
public enum NotificationScheduler {

    static let identifierPrefix = "easymeals.reminder."
    static let enabledKey = "reminders_enabled"

    public static func requestAuthorization() async -> Bool {
        await withCheckedContinuation { continuation in
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
                continuation.resume(returning: granted)
            }
        }
    }

    /// Huỷ toàn bộ nhắc việc đã lên lịch (ứng dụng chỉ dùng thông báo cho mục đích này).
    public static func disable() {
        let center = UNUserNotificationCenter.current()
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
    }

    /// Lên lịch 7 ngày kế tiếp nếu người dùng đã bật nhắc việc.
    /// Gọi lại khi mở Cài đặt để nội dung bám theo dữ liệu mới nhất.
    public static func refresh(storage: AppStorage, now: Date = Date()) {
        disable()
        guard UserDefaults.standard.bool(forKey: enabledKey) else { return }

        let center = UNUserNotificationCenter.current()
        var calendar = Calendar.current
        calendar.timeZone = .current
        let days = ReminderPlanner.upcomingTriggerDates(from: now, days: 7, calendar: calendar)

        for date in days {
            let day = ReminderPlanner.dayString(date, calendar: calendar)
            guard let digest = ReminderPlanner.buildDigest(
                pantryLots: storage.pantryLots,
                mealPlans: storage.mealPlans,
                day: day
            ) else { continue }

            let content = UNMutableNotificationContent()
            content.title = digest.title
            content.body = digest.body
            content.sound = .default

            var components = calendar.dateComponents([.year, .month, .day], from: date)
            components.hour = ReminderPlanner.reminderHour
            components.minute = 0

            let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
            let identifier = "\(identifierPrefix)\(day)"
            center.add(UNNotificationRequest(identifier: identifier, content: content, trigger: trigger))
        }
    }
}
