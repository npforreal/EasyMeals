package com.easymeals.app.domain.model

import com.google.gson.annotations.SerializedName
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.util.UUID

enum class UnitDimension {
    MASS,
    VOLUME,
    COUNT
}

@Serializable
data class Category(
    val id: String,
    val name: String,
    @SerialName("display_order") @SerializedName("display_order") val displayOrder: Int = 0
)

@Serializable
data class Conversion(
    @SerialName("from_ingredient_id") @SerializedName("from_ingredient_id") val fromIngredientId: String,
    @SerialName("to_ingredient_id") @SerializedName("to_ingredient_id") val toIngredientId: String,
    val ratio: String,
    @SerialName("from_unit") @SerializedName("from_unit") val fromUnit: String = "g",
    @SerialName("to_unit") @SerializedName("to_unit") val toUnit: String = "g",
    val note: String? = null
)

@Serializable
data class Ingredient(
    val id: String,
    val name: String,
    @SerialName("normalized_name") @SerializedName("normalized_name") val normalizedName: String,
    val category: String? = "khac",
    @SerialName("default_unit") @SerializedName("default_unit") val defaultUnit: String? = null,
    val aliases: List<String> = emptyList()
)

@Serializable
data class RecipeIngredient(
    @SerialName("ingredient_id") @SerializedName("ingredient_id") val ingredientId: String,
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    val quantity: String,
    val unit: String
)

@Serializable
data class Recipe(
    val id: String,
    val name: String,
    val category: String,
    val servings: Int = 4,
    val instructions: List<String> = emptyList(),
    val ingredients: List<RecipeIngredient> = emptyList()
)

@Serializable
data class CatalogueBundle(
    @SerialName("catalogue_version") @SerializedName("catalogue_version") val version: String? = null,
    val etag: String? = null,
    val categories: List<Category> = emptyList(),
    val conversions: List<Conversion> = emptyList(),
    val ingredients: List<Ingredient> = emptyList(),
    val recipes: List<Recipe> = emptyList()
)

@Serializable
data class PantryLot(
    val id: String = UUID.randomUUID().toString(),
    @SerialName("ingredient_id") @SerializedName("ingredient_id") val ingredientId: String,
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    @SerialName("remaining_quantity") @SerializedName("remaining_quantity") var remainingQuantity: String,
    @SerialName("purchased_quantity") @SerializedName("purchased_quantity") val purchasedQuantity: String,
    val unit: String,
    @SerialName("purchased_at") @SerializedName("purchased_at") val purchasedAt: String? = null,
    @SerialName("expires_at") @SerializedName("expires_at") val expiresAt: String? = null,
    val location: String? = "fridge"
)

@Serializable
data class StockMovement(
    val id: String = UUID.randomUUID().toString(),
    @SerialName("pantry_lot_id") @SerializedName("pantry_lot_id") val pantryLotId: String,
    @SerialName("quantity_delta") @SerializedName("quantity_delta") val quantityDelta: String,
    val reason: String,
    @SerialName("meal_plan_id") @SerializedName("meal_plan_id") val mealPlanId: String? = null,
    @SerialName("idempotency_key") @SerializedName("idempotency_key") val idempotencyKey: String? = null,
    @SerialName("created_at") @SerializedName("created_at") val createdAt: String = java.time.Instant.now().toString()
)

@Serializable
data class PlannedDish(
    val id: String = UUID.randomUUID().toString(),
    @SerialName("meal_plan_id") @SerializedName("meal_plan_id") val mealPlanId: String? = null,
    @SerialName("recipe_id") @SerializedName("recipe_id") val recipeId: String,
    @SerialName("recipe_name") @SerializedName("recipe_name") val recipeName: String,
    val category: String,
    @SerialName("is_leftover") @SerializedName("is_leftover") val isLeftover: Boolean = false,
    @SerialName("original_dish_id") @SerializedName("original_dish_id") val originalDishId: String? = null,
    val servings: Int = 4
)

@Serializable
data class MealPlan(
    val id: String = UUID.randomUUID().toString(),
    @SerialName("planned_for") @SerializedName("planned_for") val plannedFor: String,
    @SerialName("meal_period") @SerializedName("meal_period") val mealPeriod: String,
    @SerialName("period_id") @SerializedName("period_id") val periodId: String? = null,
    @SerialName("eaten_at") @SerializedName("eaten_at") var eatenAt: String? = null,
    val dishes: MutableList<PlannedDish> = mutableListOf()
)

@Serializable
data class ShoppingItem(
    @SerialName("ingredient_id") @SerializedName("ingredient_id") val ingredientId: String,
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    @SerialName("needed_quantity") @SerializedName("needed_quantity") var neededQuantity: String,
    val unit: String,
    @SerialName("is_bought") @SerializedName("is_bought") var isBought: Boolean = false,
    @SerialName("dish_names") @SerializedName("dish_names") val dishNames: MutableList<String> = mutableListOf()
) {
    val id: String get() = "${ingredientId}_$unit"
}

@Serializable
data class DeficitItem(
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    @SerialName("missing_quantity") @SerializedName("missing_quantity") val missingQuantity: String,
    val unit: String
)
