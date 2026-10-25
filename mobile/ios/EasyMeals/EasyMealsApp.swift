import SwiftUI

@main
struct EasyMealsApp: App {
    @ObservedObject private var theme = ThemeManager.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .preferredColorScheme(theme.preferredColorScheme)
                .environmentObject(theme)
                .tint(theme.paletteColors(isDark: theme.preferredColorScheme == .dark).primary)
        }
    }
}
