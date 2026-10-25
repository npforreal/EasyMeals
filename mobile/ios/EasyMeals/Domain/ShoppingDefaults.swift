import Foundation

/// A4 - Vòng 13: hạn dùng mặc định theo nhóm nguyên liệu (ngày tính từ ngày mua).
/// Dùng chung AppStorage; nhóm lạ/không rõ về 7 ngày. Khớp web & Android.
public enum ShoppingDefaults {
    public static let expiryDays: [String: Int] = [
        "thit": 3,
        "gia_cam": 2,
        "hai_san": 2,
        "trung_sua": 7,
        "rau_cu": 5,
        "cu_qua": 10,
        "gao_bot_mi": 180,
        "gia_vi": 180,
        "nuoc_cham_dau": 180,
    ]

    public static func days(category: String?) -> Int {
        guard let category, let days = expiryDays[category] else { return 7 }
        return days
    }

    /// Ngày hết hạn mặc định (ISO "yyyy-MM-dd") = ngày mua + số ngày nhóm.
    public static func expiryDate(category: String?, purchasedAt: Date = Date()) -> String {
        let day = days(category: category)
        let cal = Calendar.current
        let base = cal.startOfDay(for: purchasedAt)
        let target = cal.date(byAdding: .day, value: day, to: base) ?? base
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        formatter.timeZone = .current
        return formatter.string(from: target)
    }
}

/// A4 - Vòng 13: lượng thực mua / hạn dùng người dùng nhập cho một mục đã mua
/// khi "Cho vào tủ lạnh" (khác ước tính); chuỗi rỗng = dùng giá trị mặc định.
public struct PurchaseOverride: Identifiable, Sendable, Equatable {
    public var id: String { itemId }
    public let itemId: String
    public var actualQuantity: String
    public var expiresAt: String

    public init(itemId: String, actualQuantity: String = "", expiresAt: String = "") {
        self.itemId = itemId
        self.actualQuantity = actualQuantity
        self.expiresAt = expiresAt
    }
}
