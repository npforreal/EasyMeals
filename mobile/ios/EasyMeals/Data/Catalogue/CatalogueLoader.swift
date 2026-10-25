import Foundation

public struct CatalogueBundle: Codable, Sendable {
    public let version: String
    public let etag: String?
    public let categories: [Category]
    public let conversions: [Conversion]
    public let ingredients: [Ingredient]
    public let recipes: [Recipe]

    enum CodingKeys: String, CodingKey {
        case version = "catalogue_version"
        case legacyVersion = "version"
        case etag
        case categories
        case conversions
        case ingredients
        case recipes
    }

    public init(
        version: String,
        etag: String? = nil,
        categories: [Category] = [],
        conversions: [Conversion] = [],
        ingredients: [Ingredient] = [],
        recipes: [Recipe] = []
    ) {
        self.version = version
        self.etag = etag
        self.categories = categories
        self.conversions = conversions
        self.ingredients = ingredients
        self.recipes = recipes
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let v = try container.decodeIfPresent(String.self, forKey: .version)
            ?? container.decodeIfPresent(String.self, forKey: .legacyVersion)
            ?? "2026.10.26"
        self.version = v
        self.etag = try container.decodeIfPresent(String.self, forKey: .etag)
        self.categories = try container.decodeIfPresent([Category].self, forKey: .categories) ?? []
        self.conversions = try container.decodeIfPresent([Conversion].self, forKey: .conversions) ?? []
        self.ingredients = try container.decodeIfPresent([Ingredient].self, forKey: .ingredients) ?? []
        self.recipes = try container.decodeIfPresent([Recipe].self, forKey: .recipes) ?? []
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(version, forKey: .version)
        try container.encodeIfPresent(etag, forKey: .etag)
        try container.encode(categories, forKey: .categories)
        try container.encode(conversions, forKey: .conversions)
        try container.encode(ingredients, forKey: .ingredients)
        try container.encode(recipes, forKey: .recipes)
    }
}

public final class CatalogueLoader: Sendable {
    public static let shared = CatalogueLoader()

    public func withDefaults(_ bundle: CatalogueBundle) -> CatalogueBundle {
        var unitByIngredient: [String: String] = [:]
        for r in bundle.recipes {
            for ing in r.ingredients {
                if unitByIngredient[ing.ingredientId] == nil {
                    unitByIngredient[ing.ingredientId] = ing.unit
                }
            }
        }
        let filledIngredients = bundle.ingredients.map { ing -> Ingredient in
            var updated = ing
            if updated.defaultUnit.isEmpty {
                updated.defaultUnit = unitByIngredient[ing.id] ?? "g"
            }
            if updated.category.isEmpty {
                updated.category = "khac"
            }
            return updated
        }
        return CatalogueBundle(
            version: bundle.version,
            etag: bundle.etag,
            categories: bundle.categories,
            conversions: bundle.conversions,
            ingredients: filledIngredients,
            recipes: bundle.recipes
        )
    }

    public func loadBundledCatalogue() -> CatalogueBundle? {
        let bundle = Bundle.module
        guard let url = bundle.url(forResource: "catalogue", withExtension: "json", subdirectory: "Resources")
                ?? bundle.url(forResource: "catalogue", withExtension: "json") else {
            print("Không tìm thấy catalogue.json trong bundle Resources")
            return nil
        }
        do {
            let data = try Data(contentsOf: url)
            let decoded = try JSONDecoder().decode(CatalogueBundle.self, from: data)
            return withDefaults(decoded)
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
