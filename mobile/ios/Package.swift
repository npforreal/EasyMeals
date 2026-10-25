// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EasyMeals",
    defaultLocalization: "vi",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "EasyMealsCore",
            targets: ["EasyMealsCore"]
        ),
    ],
    targets: [
        .target(
            name: "EasyMealsCore",
            dependencies: [],
            path: "EasyMeals",
            exclude: ["UI", "EasyMealsApp.swift"],
            resources: [
                .process("Resources/catalogue.json")
            ]
        ),
        .testTarget(
            name: "EasyMealsCoreTests",
            dependencies: ["EasyMealsCore"],
            path: "EasyMealsTests",
            resources: [
                .process("Resources")
            ]
        )
    ]
)
