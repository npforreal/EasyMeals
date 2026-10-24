import Foundation

public struct CatalogueBundle: Codable, Sendable {
    public let version: String
    public let generatedAt: String
    public let ingredientsCount: Int
    public let recipesCount: Int
    public let ingredients: [Ingredient]
    public let recipes: [Recipe]

    enum CodingKeys: String, CodingKey {
        case version
        case generatedAt = "generated_at"
        case ingredientsCount = "ingredients_count"
        case recipesCount = "recipes_count"
        case ingredients
        case recipes
    }
}

public final class CatalogueLoader: Sendable {
    public static let shared = CatalogueLoader()

    public func loadBundledCatalogue() -> CatalogueBundle? {
        let bundle = Bundle.module
        guard let url = bundle.url(forResource: "catalogue", withExtension: "json", subdirectory: "Resources")
                ?? bundle.url(forResource: "catalogue", withExtension: "json") else {
            return nil
        }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(CatalogueBundle.self, from: data)
        } catch {
            print("Lỗi nạp catalogue.json: \(error)")
            return nil
        }
    }

    public static func removeDiacritics(_ str: String) -> String {
        str.folding(options: .diacriticInsensitive, locale: Locale(identifier: "vi_VN"))
            .lowercased()
            .replacingOccurrences(of: "đ", with: "d")
    }

    public static func matches(text: String, query: String) -> Bool {
        let normText = removeDiacritics(text)
        let normQuery = removeDiacritics(query).trimmingCharacters(in: .whitespacesAndNewlines)
        if normQuery.isEmpty { return true }
        return normText.contains(normQuery)
    }
}
