// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)
import SwiftUI

public struct PaletteColors {
    public let primary: Color
    public let primaryStrong: Color
    public let onPrimary: Color
    public let primarySoft: Color
}

public struct NeutralColors {
    public let bg: Color
    public let surface: Color
    public let surfaceSunken: Color
    public let ink: Color
    public let inkMuted: Color
    public let line: Color
    public let accent: Color
    public let accentSoft: Color
    public let honey: Color
    public let danger: Color
    public let dangerSoft: Color
    public let focus: Color
}

public enum GeneratedTokens {
    public enum Radius {
        public static let sm: CGFloat = 6
        public static let md: CGFloat = 10
        public static let lg: CGFloat = 16
    }

    public enum Spacing {
        public static let space_1: CGFloat = 4
        public static let space_2: CGFloat = 8
        public static let space_3: CGFloat = 12
        public static let space_4: CGFloat = 16
        public static let space_5: CGFloat = 24
        public static let space_6: CGFloat = 32
        public static let space_8: CGFloat = 48
    }

    public enum Typography {
        public static let sizeXs: CGFloat = 13
        public static let sizeSm: CGFloat = 15
        public static let sizeBase: CGFloat = 16
        public static let sizeLg: CGFloat = 20
        public static let sizeXl: CGFloat = 26
        public static let size2xl: CGFloat = 34
    }

    public enum Neutrals {
        public static let light = NeutralColors(
            bg: Color(red: 0.9647, green: 0.9451, blue: 0.9059),
            surface: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
            surfaceSunken: Color(red: 0.9294, green: 0.9020, blue: 0.8392),
            ink: Color(red: 0.1686, green: 0.1647, blue: 0.1333),
            inkMuted: Color(red: 0.4196, green: 0.3961, blue: 0.3294),
            line: Color(red: 0.8667, green: 0.8275, blue: 0.7490),
            accent: Color(red: 0.7098, green: 0.3255, blue: 0.1843),
            accentSoft: Color(red: 0.9529, green: 0.8667, blue: 0.8157),
            honey: Color(red: 0.7882, green: 0.5882, blue: 0.1686),
            danger: Color(red: 0.6078, green: 0.1725, blue: 0.1725),
            dangerSoft: Color(red: 0.9647, green: 0.8627, blue: 0.8627),
            focus: Color(red: 0.1216, green: 0.3098, blue: 0.6392)
        )
        public static let dark = NeutralColors(
            bg: Color(red: 0.1020, green: 0.1137, blue: 0.0863),
            surface: Color(red: 0.1373, green: 0.1529, blue: 0.1255),
            surfaceSunken: Color(red: 0.0902, green: 0.1020, blue: 0.0745),
            ink: Color(red: 0.9255, green: 0.9020, blue: 0.8392),
            inkMuted: Color(red: 0.6549, green: 0.6353, blue: 0.5608),
            line: Color(red: 0.2196, green: 0.2392, blue: 0.1922),
            accent: Color(red: 0.8784, green: 0.5412, blue: 0.4000),
            accentSoft: Color(red: 0.2588, green: 0.1608, blue: 0.1216),
            honey: Color(red: 0.8510, green: 0.6824, blue: 0.3059),
            danger: Color(red: 0.8784, green: 0.4392, blue: 0.4392),
            dangerSoft: Color(red: 0.2392, green: 0.1333, blue: 0.1333),
            focus: Color(red: 0.5412, green: 0.7059, blue: 1.0000)
        )
    }

    public enum Palettes {
        public enum Green {
            public static let nameVi = "Xanh lá"
            public static let light = PaletteColors(
                primary: Color(red: 0.2471, green: 0.4196, blue: 0.2275),
                primaryStrong: Color(red: 0.1843, green: 0.3333, blue: 0.1882),
                onPrimary: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
                primarySoft: Color(red: 0.8667, green: 0.9098, blue: 0.8275)
            )
            public static let dark = PaletteColors(
                primary: Color(red: 0.5608, green: 0.7490, blue: 0.5098),
                primaryStrong: Color(red: 0.6627, green: 0.8314, blue: 0.6118),
                onPrimary: Color(red: 0.0784, green: 0.1255, blue: 0.0745),
                primarySoft: Color(red: 0.1804, green: 0.2275, blue: 0.1647)
            )
        }
        public enum Terracotta {
            public static let nameVi = "Cam đất"
            public static let light = PaletteColors(
                primary: Color(red: 0.6275, green: 0.2902, blue: 0.1490),
                primaryStrong: Color(red: 0.4941, green: 0.2157, blue: 0.0941),
                onPrimary: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
                primarySoft: Color(red: 0.9647, green: 0.8706, blue: 0.7765)
            )
            public static let dark = PaletteColors(
                primary: Color(red: 0.8863, green: 0.5529, blue: 0.4078),
                primaryStrong: Color(red: 0.9412, green: 0.6549, blue: 0.5255),
                onPrimary: Color(red: 0.1294, green: 0.0784, blue: 0.0549),
                primarySoft: Color(red: 0.2588, green: 0.1608, blue: 0.1216)
            )
        }
        public enum Ocean {
            public static let nameVi = "Xanh biển"
            public static let light = PaletteColors(
                primary: Color(red: 0.1569, green: 0.3686, blue: 0.5255),
                primaryStrong: Color(red: 0.1059, green: 0.2706, blue: 0.3882),
                onPrimary: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
                primarySoft: Color(red: 0.8314, green: 0.9020, blue: 0.9451)
            )
            public static let dark = PaletteColors(
                primary: Color(red: 0.4863, green: 0.7176, blue: 0.8745),
                primaryStrong: Color(red: 0.6078, green: 0.7961, blue: 0.9216),
                onPrimary: Color(red: 0.0549, green: 0.1059, blue: 0.1490),
                primarySoft: Color(red: 0.1059, green: 0.2039, blue: 0.2824)
            )
        }
        public enum Plum {
            public static let nameVi = "Tím mận"
            public static let light = PaletteColors(
                primary: Color(red: 0.4314, green: 0.2235, blue: 0.4314),
                primaryStrong: Color(red: 0.3255, green: 0.1529, blue: 0.3255),
                onPrimary: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
                primarySoft: Color(red: 0.9176, green: 0.8431, blue: 0.9176)
            )
            public static let dark = PaletteColors(
                primary: Color(red: 0.7765, green: 0.5569, blue: 0.7765),
                primaryStrong: Color(red: 0.8510, green: 0.6745, blue: 0.8510),
                onPrimary: Color(red: 0.1294, green: 0.0667, blue: 0.1294),
                primarySoft: Color(red: 0.2588, green: 0.1294, blue: 0.2588)
            )
        }
        public enum Peach {
            public static let nameVi = "Hồng đào"
            public static let light = PaletteColors(
                primary: Color(red: 0.6118, green: 0.2627, blue: 0.3529),
                primaryStrong: Color(red: 0.4824, green: 0.1843, blue: 0.2627),
                onPrimary: Color(red: 1.0000, green: 0.9843, blue: 0.9529),
                primarySoft: Color(red: 0.9686, green: 0.8392, blue: 0.8706)
            )
            public static let dark = PaletteColors(
                primary: Color(red: 0.8745, green: 0.5216, blue: 0.6078),
                primaryStrong: Color(red: 0.9255, green: 0.6471, blue: 0.7137),
                onPrimary: Color(red: 0.1412, green: 0.0549, blue: 0.0784),
                primarySoft: Color(red: 0.2824, green: 0.1333, blue: 0.1725)
            )
        }
    }

    public enum Labels {
        public static let dish_categories: [String: String] = [
            "man": "Mặn",
            "rau": "Rau",
            "canh": "Canh"
        ]
        public static let ingredient_categories: [String: String] = [
            "thit": "Thịt",
            "gia_cam": "Gia cầm",
            "hai_san": "Hải sản",
            "trung_sua": "Trứng & Sữa",
            "rau_cu": "Rau củ",
            "cu_qua": "Củ quả",
            "gao_bot_mi": "Gạo, bột & mì",
            "gia_vi": "Gia vị",
            "nuoc_cham_dau": "Nước chấm & dầu ăn",
            "khac": "Khác"
        ]
        public static let default_expiry_days: [String: String] = [
            "thit": "3",
            "gia_cam": "3",
            "hai_san": "3",
            "trung_sua": "14",
            "rau_cu": "5",
            "cu_qua": "5",
            "gao_bot_mi": "None",
            "gia_vi": "None",
            "nuoc_cham_dau": "None",
            "khac": "None"
        ]
        public static let units: [String: String] = [
            "g": "g",
            "kg": "kg",
            "ml": "ml",
            "l": "l",
            "piece": "cái"
        ]
        public static let meal_periods: [String: String] = [
            "breakfast": "Sáng",
            "lunch": "Trưa",
            "dinner": "Tối"
        ]
        public static let palettes: [String: String] = [
            "green": "Xanh lá",
            "terracotta": "Cam đất",
            "ocean": "Xanh biển",
            "plum": "Tím mận",
            "peach": "Hồng đào"
        ]
        public static let themes: [String: String] = [
            "light": "Sáng",
            "dark": "Tối",
            "system": "Theo hệ thống"
        ]
    }

    public enum PlanLimits {
        public static let minDays: Int = 1
        public static let maxDays: Int = 7
        public static let defaultDays: Int = 3
        public static let leftoverMinDays: Int = 1
        public static let leftoverMaxDays: Int = 3
        public static let leftoverDefaultDays: Int = 2
    }
}
