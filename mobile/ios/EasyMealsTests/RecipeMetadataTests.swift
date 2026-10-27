import XCTest
@testable import EasyMealsCore

final class RecipeMetadataTests: XCTestCase {
    private func recipe(prep: Int? = nil, cook: Int? = nil, diff: String? = nil, tips: [String] = [], tipsURL: String? = nil) -> Recipe {
        Recipe(id: "r", name: "R", category: "man", prepTimeMinutes: prep,
               prepTimeSourceURL: prep == nil ? nil : "https://www.example.com/a",
               cookTimeMinutes: cook, cookTimeSourceURL: cook == nil ? nil : "https://example.com/b",
               difficulty: diff, difficultySourceURL: diff == nil ? nil : "https://www.example.com/c",
               storageTips: tips, storageSourceURL: tipsURL)
    }

    func testTotalMinutesNilHandling() {
        XCTAssertNil(RecipeMetadata.totalMinutes(prep: nil, cook: nil))
        XCTAssertEqual(RecipeMetadata.totalMinutes(prep: 10, cook: nil), 10)
        XCTAssertEqual(RecipeMetadata.totalMinutes(prep: nil, cook: 20), 20)
        XCTAssertEqual(RecipeMetadata.totalMinutes(prep: 10, cook: 20), 30)
    }

    func testMatchesTimeBoundaries() {
        for limit in [15, 30, 60] {
            XCTAssertTrue(RecipeMetadata.matchesTime(recipe(prep: limit - 5, cook: 5), maxMinutes: limit))
            XCTAssertFalse(RecipeMetadata.matchesTime(recipe(prep: limit, cook: 1), maxMinutes: limit))
        }
        XCTAssertFalse(RecipeMetadata.matchesTime(recipe(), maxMinutes: 60))
        XCTAssertTrue(RecipeMetadata.matchesTime(recipe(), maxMinutes: nil))
        XCTAssertTrue(RecipeMetadata.matchesTime(recipe(cook: 15), maxMinutes: 15))
    }

    func testMatchesDifficulty() {
        XCTAssertTrue(RecipeMetadata.matchesDifficulty(recipe(diff: "de"), difficulty: "de"))
        XCTAssertFalse(RecipeMetadata.matchesDifficulty(recipe(diff: "kho"), difficulty: "de"))
        XCTAssertFalse(RecipeMetadata.matchesDifficulty(recipe(), difficulty: "de"))
        XCTAssertTrue(RecipeMetadata.matchesDifficulty(recipe(), difficulty: nil))
    }

    func testSourceHost() {
        XCTAssertEqual(RecipeMetadata.sourceHost("https://www.fda.gov/food/x"), "fda.gov")
        XCTAssertEqual(RecipeMetadata.sourceHost("https://example.com/a"), "example.com")
        XCTAssertNil(RecipeMetadata.sourceHost(nil))
        XCTAssertNil(RecipeMetadata.sourceHost("not a url"))
    }

    func testSummaryAndNotes() {
        XCTAssertNil(RecipeMetadata.summaryLine(recipe()))
        XCTAssertEqual(RecipeMetadata.summaryLine(recipe(prep: 10, cook: 20, diff: "de")), "Chuẩn bị ~10 phút · Nấu ~20 phút · Độ khó: Dễ")
        XCTAssertEqual(RecipeMetadata.summaryLine(recipe(cook: 20)), "Nấu ~20 phút")
        XCTAssertEqual(RecipeMetadata.missingFieldsNote(recipe()), "Chưa có dữ liệu thời gian, độ khó và mẹo bảo quản.")
        XCTAssertEqual(RecipeMetadata.missingFieldsNote(recipe(prep: 5, cook: 5, diff: "de", tips: ["x"])), nil)
        XCTAssertEqual(RecipeMetadata.missingFieldsNote(recipe(prep: 5, cook: 5, diff: "de")), "Chưa có dữ liệu mẹo bảo quản.")
        XCTAssertEqual(RecipeMetadata.missingFieldsNote(recipe(prep: 5, diff: "de", tips: ["x"])), "Chưa có dữ liệu thời gian nấu.")
        XCTAssertEqual(RecipeMetadata.estimateSourceNote(recipe(prep: 5, cook: 5)), "ước lượng, nguồn: example.com")
        XCTAssertEqual(RecipeMetadata.storageSourceNote(recipe(tips: ["x"], tipsURL: "https://www.fda.gov/food/buy-store-serve-safe-food/safe-food-handling")), "Nguồn: FDA (phạm vi công cộng)")
    }

    func testUnknownCount() {
        let rs = [recipe(), recipe(prep: 5), recipe(diff: "de")]
        let c = RecipeMetadata.unknownCount(rs, timeActive: true, difficultyActive: true)
        XCTAssertEqual(c.time, 2)
        XCTAssertEqual(c.difficulty, 2)
        XCTAssertEqual(RecipeMetadata.unknownCount(rs, timeActive: false, difficultyActive: false).time, 0)
    }
}
