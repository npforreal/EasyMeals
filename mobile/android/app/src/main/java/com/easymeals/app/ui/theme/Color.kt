package com.easymeals.app.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Các màu hệ thống này giờ chỉ là alias tham chiếu GeneratedTokens (nguồn đơn thật từ design-tokens/tokens.json).
 * Các màn hình KHÔNG được import hay dùng ForestGreen / Color(0x…) trực tiếp nữa;
 * hãy lấy màu từ MaterialTheme.colorScheme (primary, onPrimary, primaryContainer, error, surfaceContainer…)
 * hoặc từ GeneratedTokens.
 */
val ForestGreen = GeneratedTokens.Palettes.Green.light.primary
val ForestGreenLight = GeneratedTokens.Palettes.Green.light.primarySoft
val WarmOrange = GeneratedTokens.Neutrals.light.accent
val SurfaceLight = GeneratedTokens.Neutrals.light.surface
val SurfaceDark = GeneratedTokens.Neutrals.dark.surface
val CardBackgroundLight = GeneratedTokens.Neutrals.light.surface
val CardBackgroundDark = GeneratedTokens.Neutrals.dark.surface
val DangerRed = GeneratedTokens.Neutrals.light.danger
