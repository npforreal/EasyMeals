package com.easymeals.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import com.easymeals.app.R

val FrauncesFontFamily = FontFamily(
    Font(R.font.fraunces, FontWeight.SemiBold)
)

val LocalEasyMealsPalette = staticCompositionLocalOf { GeneratedTokens.Palettes.Green.light }
val LocalEasyMealsNeutrals = staticCompositionLocalOf { GeneratedTokens.Neutrals.light }

fun resolvePalette(paletteName: String, isDark: Boolean): PaletteColors {
    return when (paletteName.lowercase()) {
        "terracotta" -> if (isDark) GeneratedTokens.Palettes.Terracotta.dark else GeneratedTokens.Palettes.Terracotta.light
        "ocean" -> if (isDark) GeneratedTokens.Palettes.Ocean.dark else GeneratedTokens.Palettes.Ocean.light
        "plum" -> if (isDark) GeneratedTokens.Palettes.Plum.dark else GeneratedTokens.Palettes.Plum.light
        "peach" -> if (isDark) GeneratedTokens.Palettes.Peach.dark else GeneratedTokens.Palettes.Peach.light
        else -> if (isDark) GeneratedTokens.Palettes.Green.dark else GeneratedTokens.Palettes.Green.light
    }
}

private val BaseTypography = Typography()
val AppTypography = Typography(
    headlineLarge = BaseTypography.headlineLarge.copy(fontFamily = FrauncesFontFamily),
    headlineMedium = BaseTypography.headlineMedium.copy(fontFamily = FrauncesFontFamily),
    headlineSmall = BaseTypography.headlineSmall.copy(fontFamily = FrauncesFontFamily),
    titleLarge = BaseTypography.titleLarge.copy(fontFamily = FrauncesFontFamily),
    titleMedium = BaseTypography.titleMedium.copy(fontFamily = FrauncesFontFamily),
    titleSmall = BaseTypography.titleSmall.copy(fontFamily = FrauncesFontFamily)
)

@Composable
fun EasyMealsTheme(
    themeMode: String = "system",
    palette: String = "green",
    content: @Composable () -> Unit
) {
    val systemInDark = isSystemInDarkTheme()
    val isDark = when (themeMode.lowercase()) {
        "light" -> false
        "dark" -> true
        else -> systemInDark
    }

    val paletteColors = resolvePalette(palette, isDark)
    val neutrals = if (isDark) GeneratedTokens.Neutrals.dark else GeneratedTokens.Neutrals.light

    val colorScheme = if (isDark) {
        darkColorScheme(
            primary = paletteColors.primary,
            onPrimary = paletteColors.onPrimary,
            primaryContainer = paletteColors.primarySoft,
            onPrimaryContainer = paletteColors.primaryStrong,
            secondary = neutrals.accent,
            background = neutrals.bg,
            surface = neutrals.surface,
            surfaceVariant = neutrals.surfaceSunken,
            onSurface = neutrals.ink,
            onSurfaceVariant = neutrals.inkMuted,
            outline = neutrals.line,
            error = neutrals.danger
        )
    } else {
        lightColorScheme(
            primary = paletteColors.primary,
            onPrimary = paletteColors.onPrimary,
            primaryContainer = paletteColors.primarySoft,
            onPrimaryContainer = paletteColors.primaryStrong,
            secondary = neutrals.accent,
            background = neutrals.bg,
            surface = neutrals.surface,
            surfaceVariant = neutrals.surfaceSunken,
            onSurface = neutrals.ink,
            onSurfaceVariant = neutrals.inkMuted,
            outline = neutrals.line,
            error = neutrals.danger
        )
    }

    CompositionLocalProvider(
        LocalEasyMealsPalette provides paletteColors,
        LocalEasyMealsNeutrals provides neutrals
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = AppTypography,
            content = content
        )
    }
}
