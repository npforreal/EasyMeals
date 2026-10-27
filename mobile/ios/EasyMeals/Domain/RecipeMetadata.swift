import Foundation

/// Logic thuần cho metadata công thức (thời gian, độ khó, mẹo bảo quản). Khớp Web/Android.
/// Giá trị thời gian/độ khó là ước lượng từ nghiên cứu web; không tự suy diễn thêm.
public enum RecipeMetadata {
    /// Tổng phút = chuẩn bị + nấu, phần nil tính 0; cả hai nil => nil (chưa có dữ liệu).
    public static func totalMinutes(prep: Int?, cook: Int?) -> Int? {
        if prep == nil && cook == nil { return nil }
        return (prep ?? 0) + (cook ?? 0)
    }

    public static func totalMinutes(_ r: Recipe) -> Int? {
        totalMinutes(prep: r.prepTimeMinutes, cook: r.cookTimeMinutes)
    }

    /// maxMinutes nil = "Tất cả". Công thức chưa có dữ liệu bị loại khi lọc đang bật.
    public static func matchesTime(_ r: Recipe, maxMinutes: Int?) -> Bool {
        guard let maxMinutes else { return true }
        guard let total = totalMinutes(r) else { return false }
        return total <= maxMinutes
    }

    /// difficulty nil = "Tất cả".
    public static func matchesDifficulty(_ r: Recipe, difficulty: String?) -> Bool {
        guard let difficulty else { return true }
        return r.difficulty == difficulty
    }

    public static func difficultyLabel(_ key: String?) -> String? {
        switch key {
        case "de": return "Dễ"
        case "trung_binh": return "Trung bình"
        case "kho": return "Khó"
        default: return nil
        }
    }

    /// Hostname của URL nguồn (bỏ "www."), nil nếu không hợp lệ.
    public static func sourceHost(_ url: String?) -> String? {
        guard let url, let host = URL(string: url)?.host, !host.isEmpty else { return nil }
        return host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
    }

    /// Số món bị ẩn vì thiếu dữ liệu khi lọc thời gian/độ khó đang bật.
    public static func unknownCount(_ recipes: [Recipe], timeActive: Bool, difficultyActive: Bool) -> (time: Int, difficulty: Int) {
        (timeActive ? recipes.filter { totalMinutes($0) == nil }.count : 0,
         difficultyActive ? recipes.filter { difficultyLabel($0.difficulty) == nil }.count : 0)
    }

    public static func hiddenNote(count: Int, label: String) -> String {
        "\(count) món chưa có dữ liệu \(label) nên bị ẩn."
    }

    /// Dòng "Chuẩn bị ~X phút · Nấu ~Y phút · Độ khó: Dễ" chỉ gồm trường có dữ liệu; nil nếu không có gì.
    public static func summaryLine(_ r: Recipe) -> String? {
        var parts: [String] = []
        if let p = r.prepTimeMinutes { parts.append("Chuẩn bị ~\(p) phút") }
        if let c = r.cookTimeMinutes { parts.append("Nấu ~\(c) phút") }
        if let d = difficultyLabel(r.difficulty) { parts.append("Độ khó: \(d)") }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    /// "ước lượng, nguồn: host" (các host khác nhau được gộp); nil nếu không có nguồn.
    public static func estimateSourceNote(_ r: Recipe) -> String? {
        var hosts: [String] = []
        let urls = [r.prepTimeMinutes != nil ? r.prepTimeSourceURL : nil,
                    r.cookTimeMinutes != nil ? r.cookTimeSourceURL : nil,
                    difficultyLabel(r.difficulty) != nil ? r.difficultySourceURL : nil]
        for u in urls {
            if let h = sourceHost(u), !hosts.contains(h) { hosts.append(h) }
        }
        return hosts.isEmpty ? "ước lượng" : "ước lượng, nguồn: " + hosts.joined(separator: ", ")
    }

    /// Ghi chú chỉ nêu các trường thực sự thiếu; nil nếu đủ cả ba.
    public static func missingFieldsNote(_ r: Recipe) -> String? {
        var missing: [String] = []
        if r.prepTimeMinutes == nil && r.cookTimeMinutes == nil {
            missing.append("thời gian")
        } else if r.prepTimeMinutes == nil {
            missing.append("thời gian chuẩn bị")
        } else if r.cookTimeMinutes == nil {
            missing.append("thời gian nấu")
        }
        if difficultyLabel(r.difficulty) == nil { missing.append("độ khó") }
        if r.storageTips.isEmpty { missing.append("mẹo bảo quản") }
        if missing.isEmpty { return nil }
        let list: String
        if missing.count > 1 {
            list = missing.dropLast().joined(separator: ", ") + " và " + missing.last!
        } else { list = missing[0] }
        return "Chưa có dữ liệu \(list)."
    }

    public static func storageSourceNote(_ r: Recipe) -> String? {
        guard let host = sourceHost(r.storageSourceURL) else { return nil }
        if host.hasSuffix("fda.gov") { return "Nguồn: FDA (phạm vi công cộng)" }
        return "Nguồn: \(host)"
    }
}
