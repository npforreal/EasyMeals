import Foundation

public struct ExpiryStatus {
    public let text: String
    public let isWarning: BooleanLiteralType
    public let isExpired: BooleanLiteralType
    public let daysRemaining: Int

    public init(text: String, isWarning: Bool, isExpired: Bool, daysRemaining: Int) {
        self.text = text
        self.isWarning = isWarning
        self.isExpired = isExpired
        self.daysRemaining = daysRemaining
    }
}

public enum AppDateFormatter {
    private static let ddmmyyyy: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "dd/MM/yyyy"
        f.locale = Locale(identifier: "vi_VN")
        return f
    }()

    private static let ddmm: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "dd/MM"
        f.locale = Locale(identifier: "vi_VN")
        return f
    }()

    private static let isoDate: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    public static func formatDateVN(_ dateStr: String?) -> String {
        guard let s = dateStr?.prefix(10), let date = isoDate.date(from: String(s)) else {
            return dateStr ?? ""
        }
        return ddmmyyyy.string(from: date)
    }

    public static func formatRelativeDate(_ dateStr: String?, today: Date = Date()) -> String {
        guard let s = dateStr?.prefix(10), let date = isoDate.date(from: String(s)) else {
            return dateStr ?? ""
        }
        let cal = Calendar.current
        let startOfToday = cal.startOfDay(for: today)
        let startOfTarget = cal.startOfDay(for: date)
        let diff = cal.dateComponents([.day], from: startOfToday, to: startOfTarget).day ?? 0

        let shortDate = ddmm.string(from: date)
        switch diff {
        case 0:
            return "Hôm nay, \(shortDate)"
        case 1:
            return "Ngày mai, \(shortDate)"
        case -1:
            return "Hôm qua, \(shortDate)"
        default:
            let weekday = cal.component(.weekday, from: date)
            let dow: String
            switch weekday {
            case 1: dow = "CN"
            case 2: dow = "T2"
            case 3: dow = "T3"
            case 4: dow = "T4"
            case 5: dow = "T5"
            case 6: dow = "T6"
            case 7: dow = "T7"
            default: dow = ""
            }
            return "\(dow) \(shortDate)"
        }
    }

    public static func formatExpiryStatus(_ dateStr: String?, today: Date = Date()) -> ExpiryStatus? {
        guard let s = dateStr?.prefix(10), let date = isoDate.date(from: String(s)) else {
            return nil
        }
        let cal = Calendar.current
        let startOfToday = cal.startOfDay(for: today)
        let startOfTarget = cal.startOfDay(for: date)
        let diff = cal.dateComponents([.day], from: startOfToday, to: startOfTarget).day ?? 0
        let formatted = ddmmyyyy.string(from: date)

        if diff < 0 {
            return ExpiryStatus(
                text: "Quá hạn \(-diff) ngày (\(formatted))",
                isWarning: true,
                isExpired: true,
                daysRemaining: diff
            )
        } else if diff == 0 {
            return ExpiryStatus(
                text: "Hết hạn hôm nay (\(formatted))",
                isWarning: true,
                isExpired: true,
                daysRemaining: 0
            )
        } else if diff == 1 {
            return ExpiryStatus(
                text: "Hết hạn ngày mai (\(formatted))",
                isWarning: true,
                isExpired: false,
                daysRemaining: 1
            )
        } else if diff == 2 {
            return ExpiryStatus(
                text: "Còn 2 ngày (\(formatted))",
                isWarning: true,
                isExpired: false,
                daysRemaining: 2
            )
        } else {
            return ExpiryStatus(
                text: "Còn \(diff) ngày (\(formatted))",
                isWarning: false,
                isExpired: false,
                daysRemaining: diff
            )
        }
    }
}
