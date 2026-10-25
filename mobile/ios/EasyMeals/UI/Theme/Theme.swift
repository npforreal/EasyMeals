import SwiftUI

public class ThemeManager: ObservableObject {
    public static let shared = ThemeManager()

    @AppStorage("theme_mode") public var themeMode: String = "system"
    @AppStorage("theme_palette") public var palette: String = "green"

    public var preferredColorScheme: ColorScheme? {
        switch themeMode.lowercased() {
        case "light": return .light
        case "dark": return .dark
        default: return nil
        }
    }

    public func paletteColors(isDark: Bool) -> PaletteColors {
        switch palette.lowercased() {
        case "terracotta":
            return isDark ? GeneratedTokens.Palettes.Terracotta.dark : GeneratedTokens.Palettes.Terracotta.light
        case "ocean":
            return isDark ? GeneratedTokens.Palettes.Ocean.dark : GeneratedTokens.Palettes.Ocean.light
        case "plum":
            return isDark ? GeneratedTokens.Palettes.Plum.dark : GeneratedTokens.Palettes.Plum.light
        case "peach":
            return isDark ? GeneratedTokens.Palettes.Peach.dark : GeneratedTokens.Palettes.Peach.light
        default:
            return isDark ? GeneratedTokens.Palettes.Green.dark : GeneratedTokens.Palettes.Green.light
        }
    }

    public func neutrals(isDark: Bool) -> NeutralColors {
        isDark ? GeneratedTokens.Neutrals.dark : GeneratedTokens.Neutrals.light
    }
}

public enum AppColors {
    public static var primary: Color {
        let pal = UserDefaults.standard.string(forKey: "theme_palette") ?? "green"
        let isDark = (UserDefaults.standard.string(forKey: "theme_mode") == "dark")
        return ThemeManager.shared.paletteColors(isDark: isDark).primary
    }

    public static var primaryLight: Color {
        let pal = UserDefaults.standard.string(forKey: "theme_palette") ?? "green"
        let isDark = (UserDefaults.standard.string(forKey: "theme_mode") == "dark")
        return ThemeManager.shared.paletteColors(isDark: isDark).primarySoft
    }

    public static var accent: Color {
        let isDark = (UserDefaults.standard.string(forKey: "theme_mode") == "dark")
        return isDark ? GeneratedTokens.Neutrals.dark.accent : GeneratedTokens.Neutrals.light.accent
    }

    public static var surface = Color(UIColor.systemBackground)
    public static let secondarySurface = Color(UIColor.secondarySystemBackground)
    public static let tertiarySurface = Color(UIColor.tertiarySystemBackground)
    public static let textPrimary = Color(UIColor.label)
    public static let textSecondary = Color(UIColor.secondaryLabel)

    public static var danger: Color {
        let isDark = (UserDefaults.standard.string(forKey: "theme_mode") == "dark")
        return isDark ? GeneratedTokens.Neutrals.dark.danger : GeneratedTokens.Neutrals.light.danger
    }

    public static var warning: Color {
        let isDark = (UserDefaults.standard.string(forKey: "theme_mode") == "dark")
        return isDark ? GeneratedTokens.Neutrals.dark.honey : GeneratedTokens.Neutrals.light.honey
    }
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

public extension Font {
    static func fraunces(size: CGFloat) -> Font {
        Font.custom("Fraunces", size: size)
    }
}
