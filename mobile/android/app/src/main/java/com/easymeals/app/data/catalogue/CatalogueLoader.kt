package com.easymeals.app.data.catalogue

import android.content.Context
import com.easymeals.app.domain.model.CatalogueBundle
import kotlinx.serialization.json.Json
import java.io.InputStream
import java.text.Normalizer
import java.util.regex.Pattern

private val jsonParser = Json {
    ignoreUnknownKeys = true
    isLenient = true
    coerceInputValues = true
}

/**
 * Điền giá trị mặc định và suy ra defaultUnit từ các công thức nếu danh mục chưa có.
 */
fun CatalogueBundle.withDefaults(): CatalogueBundle {
    val unitByIngredient: Map<String, String> = recipes
        .flatMap { it.ingredients }
        .groupBy { it.ingredientId }
        .mapValues { (_, uses) ->
            uses.groupingBy { it.unit }.eachCount().maxByOrNull { it.value }?.key ?: "g"
        }
    return copy(
        ingredients = ingredients.map { ing ->
            ing.copy(
                defaultUnit = if (!ing.defaultUnit.isNullOrBlank()) ing.defaultUnit else unitByIngredient[ing.id] ?: "g",
                category = if (!ing.category.isNullOrBlank()) ing.category else "khac"
            )
        }
    )
}

object CatalogueLoader {

    var lastError: String? = null
        private set

    fun loadCatalogue(stream: InputStream): CatalogueBundle {
        val jsonText = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        val bundle = jsonParser.decodeFromString<CatalogueBundle>(jsonText)
        return bundle.withDefaults()
    }

    fun loadBundledCatalogue(context: Context): CatalogueBundle? {
        lastError = null
        return try {
            val stream = context.assets.open("catalogue.json")
            loadCatalogue(stream)
        } catch (e: Exception) {
            e.printStackTrace()
            lastError = e.localizedMessage ?: e.toString()
            null
        }
    }

    private val DIACRITICS_PATTERN = Pattern.compile("\\p{InCombiningDiacriticalMarks}+")

    fun removeDiacritics(str: String): String {
        val normalized = Normalizer.normalize(str, Normalizer.Form.NFD)
        return DIACRITICS_PATTERN.matcher(normalized)
            .replaceAll("")
            .replace('đ', 'd')
            .replace('Đ', 'D')
            .lowercase()
            .trim()
    }

    fun matches(text: String, query: String): Boolean {
        val normText = removeDiacritics(text)
        val normQuery = removeDiacritics(query)
        if (normQuery.isBlank()) return true
        return normText.contains(normQuery)
    }
}
