import Foundation

/// Số học Decimal chính xác dựa trên Foundation.Decimal.
/// Đồng nhất với Python `Decimal` và JavaScript `Decimal` trong EasyMeals Engine.
public struct ExactDecimal: Comparable, CustomStringConvertible, Codable, Sendable, Hashable {
    public var value: Decimal

    public init(_ string: String) {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
        self.value = Decimal(string: trimmed) ?? Decimal.zero
    }

    public init(_ intVal: Int) {
        self.value = Decimal(intVal)
    }

    public init(_ int64Val: Int64) {
        self.value = Decimal(int64Val)
    }

    public init(_ decimalVal: Decimal) {
        self.value = decimalVal
    }

    public static let zero = ExactDecimal(Decimal.zero)
    public static let one = ExactDecimal(Decimal(1))

    public static func + (lhs: ExactDecimal, rhs: ExactDecimal) -> ExactDecimal {
        ExactDecimal(lhs.value + rhs.value)
    }

    public static func - (lhs: ExactDecimal, rhs: ExactDecimal) -> ExactDecimal {
        ExactDecimal(lhs.value - rhs.value)
    }

    public static func * (lhs: ExactDecimal, rhs: ExactDecimal) -> ExactDecimal {
        ExactDecimal(lhs.value * rhs.value)
    }

    public static func / (lhs: ExactDecimal, rhs: ExactDecimal) -> ExactDecimal {
        guard rhs.value != 0 else { fatalError("Phép chia cho 0 trong ExactDecimal") }
        return ExactDecimal(lhs.value / rhs.value)
    }

    public static func < (lhs: ExactDecimal, rhs: ExactDecimal) -> Bool {
        lhs.value < rhs.value
    }

    public static func == (lhs: ExactDecimal, rhs: ExactDecimal) -> Bool {
        lhs.value == rhs.value
    }

    public func abs() -> ExactDecimal {
        ExactDecimal(Swift.abs(self.value))
    }

    public var description: String {
        // Định dạng chuỗi không có đuôi .000 dư thừa
        let str = "\(value)"
        if str.contains(".") {
            var trimmed = str
            while trimmed.hasSuffix("0") {
                trimmed.removeLast()
            }
            if trimmed.hasSuffix(".") {
                trimmed.removeLast()
            }
            return trimmed
        }
        return str
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let str = try? container.decode(String.self) {
            self = ExactDecimal(str)
        } else if let intVal = try? container.decode(Int.self) {
            self = ExactDecimal(intVal)
        } else if let decVal = try? container.decode(Decimal.self) {
            self = ExactDecimal(decVal)
        } else {
            self = .zero
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(description)
    }
}
