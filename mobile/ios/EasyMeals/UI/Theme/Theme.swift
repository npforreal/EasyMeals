import SwiftUI

public enum AppColors {
    public static let primary = Color(red: 0.18, green: 0.49, blue: 0.20) // #2E7D32 Emerald
    public static let primaryLight = Color(red: 0.78, green: 0.90, blue: 0.79)
    public static let accent = Color(red: 0.96, green: 0.50, blue: 0.09) // Warm orange
    public static let surface = Color(UIColor.systemBackground)
    public static let secondarySurface = Color(UIColor.secondarySystemBackground)
    public static let tertiarySurface = Color(UIColor.tertiarySystemBackground)
    public static let textPrimary = Color(UIColor.label)
    public static let textSecondary = Color(UIColor.secondaryLabel)
    public static let danger = Color(red: 0.85, green: 0.20, blue: 0.18)
    public static let warning = Color(red: 0.95, green: 0.65, blue: 0.15)
}

public struct CardModifier: ViewModifier {
    public func body(content: Content) -> some View {
        content
            .padding()
            .background(AppColors.secondarySurface)
            .cornerRadius(16)
            .shadow(color: Color.black.opacity(0.04), radius: 8, x: 0, y: 2)
    }
}

public extension View {
    func cardStyle() -> some View {
        modifier(CardModifier())
    }
}
