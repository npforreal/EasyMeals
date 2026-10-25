// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)
package com.easymeals.app.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class PaletteColors(
    val primary: Color,
    val primaryStrong: Color,
    val onPrimary: Color,
    val primarySoft: Color
)

data class NeutralColors(
    val bg: Color,
    val surface: Color,
    val surfaceSunken: Color,
    val ink: Color,
    val inkMuted: Color,
    val line: Color,
    val accent: Color,
    val accentSoft: Color,
    val honey: Color,
    val danger: Color,
    val dangerSoft: Color,
    val focus: Color
)

object GeneratedTokens {
    object Radius {
        val sm: Dp = 6.dp
        val md: Dp = 10.dp
        val lg: Dp = 16.dp
    }

    object Spacing {
        val space_1: Dp = 4.dp
        val space_2: Dp = 8.dp
        val space_3: Dp = 12.dp
        val space_4: Dp = 16.dp
        val space_5: Dp = 24.dp
        val space_6: Dp = 32.dp
        val space_8: Dp = 48.dp
    }

    object Typography {
        val sizeXs: TextUnit = 13.sp
        val sizeSm: TextUnit = 15.sp
        val sizeBase: TextUnit = 16.sp
        val sizeLg: TextUnit = 20.sp
        val sizeXl: TextUnit = 26.sp
        val size2xl: TextUnit = 34.sp
    }

    object Neutrals {
        val light = NeutralColors(
            bg = Color(0xFFF6F1E7),
            surface = Color(0xFFFFFBF3),
            surfaceSunken = Color(0xFFEDE6D6),
            ink = Color(0xFF2B2A22),
            inkMuted = Color(0xFF6B6554),
            line = Color(0xFFDDD3BF),
            accent = Color(0xFFB5532F),
            accentSoft = Color(0xFFF3DDD0),
            honey = Color(0xFFC9962B),
            danger = Color(0xFF9B2C2C),
            dangerSoft = Color(0xFFF6DCDC),
            focus = Color(0xFF1F4FA3)
        )
        val dark = NeutralColors(
            bg = Color(0xFF1A1D16),
            surface = Color(0xFF232720),
            surfaceSunken = Color(0xFF171A13),
            ink = Color(0xFFECE6D6),
            inkMuted = Color(0xFFA7A28F),
            line = Color(0xFF383D31),
            accent = Color(0xFFE08A66),
            accentSoft = Color(0xFF42291F),
            honey = Color(0xFFD9AE4E),
            danger = Color(0xFFE07070),
            dangerSoft = Color(0xFF3D2222),
            focus = Color(0xFF8AB4FF)
        )
    }

    object Palettes {
        object Green {
            const val NAME_VI = "Xanh lá"
            val light = PaletteColors(
                primary = Color(0xFF3F6B3A),
                primaryStrong = Color(0xFF2F5530),
                onPrimary = Color(0xFFFFFBF3),
                primarySoft = Color(0xFFDDE8D3)
            )
            val dark = PaletteColors(
                primary = Color(0xFF8FBF82),
                primaryStrong = Color(0xFFA9D49C),
                onPrimary = Color(0xFF142013),
                primarySoft = Color(0xFF2E3A2A)
            )
        }
        object Terracotta {
            const val NAME_VI = "Cam đất"
            val light = PaletteColors(
                primary = Color(0xFFA04A26),
                primaryStrong = Color(0xFF7E3718),
                onPrimary = Color(0xFFFFFBF3),
                primarySoft = Color(0xFFF6DEC6)
            )
            val dark = PaletteColors(
                primary = Color(0xFFE28D68),
                primaryStrong = Color(0xFFF0A786),
                onPrimary = Color(0xFF21140E),
                primarySoft = Color(0xFF42291F)
            )
        }
        object Ocean {
            const val NAME_VI = "Xanh biển"
            val light = PaletteColors(
                primary = Color(0xFF285E86),
                primaryStrong = Color(0xFF1B4563),
                onPrimary = Color(0xFFFFFBF3),
                primarySoft = Color(0xFFD4E6F1)
            )
            val dark = PaletteColors(
                primary = Color(0xFF7CB7DF),
                primaryStrong = Color(0xFF9BCBEB),
                onPrimary = Color(0xFF0E1B26),
                primarySoft = Color(0xFF1B3448)
            )
        }
        object Plum {
            const val NAME_VI = "Tím mận"
            val light = PaletteColors(
                primary = Color(0xFF6E396E),
                primaryStrong = Color(0xFF532753),
                onPrimary = Color(0xFFFFFBF3),
                primarySoft = Color(0xFFEAD7EA)
            )
            val dark = PaletteColors(
                primary = Color(0xFFC68EC6),
                primaryStrong = Color(0xFFD9ACD9),
                onPrimary = Color(0xFF211121),
                primarySoft = Color(0xFF422142)
            )
        }
        object Peach {
            const val NAME_VI = "Hồng đào"
            val light = PaletteColors(
                primary = Color(0xFF9C435A),
                primaryStrong = Color(0xFF7B2F43),
                onPrimary = Color(0xFFFFFBF3),
                primarySoft = Color(0xFFF7D6DE)
            )
            val dark = PaletteColors(
                primary = Color(0xFFDF859B),
                primaryStrong = Color(0xFFECA5B6),
                onPrimary = Color(0xFF240E14),
                primarySoft = Color(0xFF48222C)
            )
        }
    }

    object Labels {
        val dish_categories: Map<String, String> = mapOf(
            "man" to "Mặn",
            "rau" to "Rau",
            "canh" to "Canh"
        )
        val ingredient_categories: Map<String, String> = mapOf(
            "thit" to "Thịt",
            "gia_cam" to "Gia cầm",
            "hai_san" to "Hải sản",
            "trung_sua" to "Trứng & Sữa",
            "rau_cu" to "Rau củ",
            "cu_qua" to "Củ quả",
            "gao_bot_mi" to "Gạo, bột & mì",
            "gia_vi" to "Gia vị",
            "nuoc_cham_dau" to "Nước chấm & dầu ăn",
            "khac" to "Khác"
        )
        val default_expiry_days: Map<String, String> = mapOf(
            "thit" to "3",
            "gia_cam" to "3",
            "hai_san" to "3",
            "trung_sua" to "14",
            "rau_cu" to "5",
            "cu_qua" to "5",
            "gao_bot_mi" to "None",
            "gia_vi" to "None",
            "nuoc_cham_dau" to "None",
            "khac" to "None"
        )
        val units: Map<String, String> = mapOf(
            "g" to "g",
            "kg" to "kg",
            "ml" to "ml",
            "l" to "l",
            "piece" to "cái"
        )
        val meal_periods: Map<String, String> = mapOf(
            "breakfast" to "Sáng",
            "lunch" to "Trưa",
            "dinner" to "Tối"
        )
        val palettes: Map<String, String> = mapOf(
            "green" to "Xanh lá",
            "terracotta" to "Cam đất",
            "ocean" to "Xanh biển",
            "plum" to "Tím mận",
            "peach" to "Hồng đào"
        )
        val themes: Map<String, String> = mapOf(
            "light" to "Sáng",
            "dark" to "Tối",
            "system" to "Theo hệ thống"
        )
    }
}
