package com.easymeals.app.domain.model

import com.google.gson.annotations.SerializedName
import java.util.UUID

enum class UnitDimension {
    MASS,
    VOLUME,
    COUNT
}

data class Ingredient(
    val id: String,
    val name: String,
    @SerializedName("normalized_name") val normalizedName: String,
    val category: String,
    @SerializedName("default_unit") val defaultUnit: String
)

data class RecipeIngredient(
    @SerializedName("ingredient_id") val ingredientId: String,
    @SerializedName("ingredient_name") val ingredientName: String,
    val quantity: String,
    val unit: String
)

data class Recipe(
    val id: String,
    val name: String,
    val category: String,
    val servings: Int = 4,
    val instructions: List<String> = emptyList(),
    val ingredients: List<RecipeIngredient> = emptyList()
)

data class PantryLot(
    val id: String = UUID.randomUUID().toString(),
    @SerializedName("ingredient_id") val ingredientId: String,
    @SerializedName("ingredient_name") val ingredientName: String,
    @SerializedName("remaining_quantity") var remainingQuantity: String,
    @SerializedName("purchased_quantity") val purchasedQuantity: String,
    val unit: String,
    @SerializedName("purchased_at") val purchasedAt: String? = null,
    @SerializedName("expires_at") val expiresAt: String? = null,
    val location: String? = "fridge"
)

data class StockMovement(
    val id: String = UUID.randomUUID().toString(),
    @SerializedName("pantry_lot_id") val pantryLotId: String,
    @SerializedName("quantity_delta") val quantityDelta: String,
    val reason: String,
    @SerializedName("meal_plan_id") val mealPlanId: String? = null,
    @SerializedName("idempotency_key") val idempotencyKey: String? = null,
    @SerializedName("created_at") val createdAt: String = java.time.Instant.now().toString()
)

data class PlannedDish(
    val id: String = UUID.randomUUID().toString(),
    @SerializedName("meal_plan_id") val mealPlanId: String? = null,
    @SerializedName("recipe_id") val recipeId: String,
    @SerializedName("recipe_name") val recipeName: String,
    val category: String,
    @SerializedName("is_leftover") val isLeftover: Boolean = false,
    @SerializedName("original_dish_id") val originalDishId: String? = null,
    val servings: Int = 4
)

data class MealPlan(
    val id: String = UUID.randomUUID().toString(),
    @SerializedName("planned_for") val plannedFor: String,
    @SerializedName("meal_period") val mealPeriod: String,
    @SerializedName("period_id") val periodId: String? = null,
    @SerializedName("eaten_at") var eatenAt: String? = null,
    val dishes: MutableList<PlannedDish> = mutableListOf()
)

data class ShoppingItem(
    @SerializedName("ingredient_id") val ingredientId: String,
    @SerializedName("ingredient_name") val ingredientName: String,
    @SerializedName("needed_quantity") var neededQuantity: String,
    val unit: String,
    @SerializedName("is_bought") var isBought: Boolean = false,
    @SerializedName("dish_names") val dishNames: MutableList<String> = mutableListOf()
) {
    val id: String get() = "${ingredientId}_$unit"
}

data class DeficitItem(
    @SerializedName("ingredient_name") val ingredientName: String,
    @SerializedName("missing_quantity") val missingQuantity: String,
    val unit: String
)
