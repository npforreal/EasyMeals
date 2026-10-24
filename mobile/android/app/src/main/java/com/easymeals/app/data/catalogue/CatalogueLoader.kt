package com.easymeals.app.data.catalogue

import android.content.Context
import com.easymeals.app.domain.model.Ingredient
import com.easymeals.app.domain.model.Recipe
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.io.InputStreamReader
import java.text.Normalizer
import java.util.regex.Pattern

data class CatalogueBundle(
    val version: String,
    @SerializedName("generated_at") val generatedAt: String,
    @SerializedName("ingredients_count") val ingredientsCount: Int,
    @SerializedName("recipes_count") val recipesCount: Int,
    val ingredients: List<Ingredient>,
    val recipes: List<Recipe>
)

object CatalogueLoader {
    private val gson = Gson()

    fun loadBundledCatalogue(context: Context): CatalogueBundle? {
        return try {
            val stream = context.assets.open("catalogue.json")
            val reader = InputStreamReader(stream, Charsets.UTF_8)
            gson.fromJson(reader, CatalogueBundle::class.java)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun removeDiacritics(str: String): String {
        val nfdNormalizedString = Normalizer.normalize(str, Normalizer.Form.NFD)
        val pattern = Pattern.compile("\\p{InCombiningDiacriticalMarks}+")
        return pattern.matcher(nfdNormalizedString)
            .replaceAll("")
            .lowercase()
            .replace('đ', 'd')
            .replace('Đ', 'd')
    }

    fun matches(text: String, query: String): Boolean {
        val normText = removeDiacritics(text)
        val normQuery = removeDiacritics(query).trim()
        if (normQuery.isEmpty()) return true
        return normText.contains(normQuery)
    }
}
