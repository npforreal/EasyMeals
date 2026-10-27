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
    val aliases: List<String> = emptyList(),
    val allergens: List<String> = emptyList(),
    @SerialName("allergen_verification_status") val allergenVerificationStatus: String = "unknown",
    @SerialName("allergen_source_url") val allergenSourceUrl: String? = null,
    @SerialName("allergen_verified_at") val allergenVerifiedAt: String? = null
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
    val ingredients: List<RecipeIngredient> = emptyList(),
    @SerialName("dietary_status") val dietaryStatus: String = "unknown",
    @SerialName("dietary_source_url") val dietarySourceUrl: String? = null,
    @SerialName("dietary_verified_at") val dietaryVerifiedAt: String? = null,
    @SerialName("spice_level") val spiceLevel: Int? = null,
    @SerialName("spice_source_url") val spiceSourceUrl: String? = null,
    @SerialName("spice_verified_at") val spiceVerifiedAt: String? = null,
    // E2-data: thời gian chuẩn bị, thời gian nấu, độ khó (nguồn và ngày xác minh đi kèm)
    @SerialName("prep_time_minutes") val prepTimeMinutes: Int? = null,
    @SerialName("prep_time_source_url") val prepTimeSourceUrl: String? = null,
    @SerialName("prep_time_verified_at") val prepTimeVerifiedAt: String? = null,
    @SerialName("cook_time_minutes") val cookTimeMinutes: Int? = null,
    @SerialName("cook_time_source_url") val cookTimeSourceUrl: String? = null,
    @SerialName("cook_time_verified_at") val cookTimeVerifiedAt: String? = null,
    @SerialName("difficulty") val difficulty: String? = null,
    @SerialName("difficulty_source_url") val difficultySourceUrl: String? = null,
    @SerialName("difficulty_verified_at") val difficultyVerifiedAt: String? = null,
    // E3-data: mẹo bảo quản (nguồn và ngày xác minh đi kèm)
    @SerialName("storage_tips") val storageTips: List<String> = emptyList(),
    @SerialName("storage_source_url") val storageSourceUrl: String? = null,
    @SerialName("storage_verified_at") val storageVerifiedAt: String? = null
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
    val servings: Int = 4,
    @SerialName("selection_reason") @SerializedName("selection_reason") val selectionReason: String? = null
)

@Serializable
data class MealPlan(
    val id: String = UUID.randomUUID().toString(),
    @SerialName("planned_for") @SerializedName("planned_for") val plannedFor: String,
    @SerialName("meal_period") @SerializedName("meal_period") val mealPeriod: String,
    @SerialName("period_id") @SerializedName("period_id") val periodId: String? = null,
    @SerialName("eaten_at") @SerializedName("eaten_at") var eatenAt: String? = null,
    val notes: String? = null,
    val dishes: MutableList<PlannedDish> = mutableListOf(),
    val warnings: List<PlanWarning>? = null
)

@Serializable
data class PlanWarning(
    val type: String,
    @SerialName("planned_for") val plannedFor: String,
    @SerialName("meal_period") val mealPeriod: String,
    val reason: String
)

data class PlanGenerationResult(
    val periodId: String,
    val plans: List<MealPlan>,
    val shoppingList: List<ShoppingItem>,
    val excludedRecipeCount: Int,
    val warnings: List<PlanWarning>
)

@Serializable
data class ShoppingItem(
    @SerialName("ingredient_id") @SerializedName("ingredient_id") val ingredientId: String,
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    @SerialName("needed_quantity") @SerializedName("needed_quantity") var neededQuantity: String,
    val unit: String,
    @SerialName("is_bought") @SerializedName("is_bought") var isBought: Boolean = false,
    // A3 - Vòng 13: nguồn phát sinh — người dùng tự thêm thì giữ khi kế hoạch đổi.
    @SerialName("is_manually_added") @SerializedName("is_manually_added") var isManuallyAdded: Boolean = false,
    @SerialName("dish_names") @SerializedName("dish_names") val dishNames: MutableList<String> = mutableListOf(),
    val category: String? = "khac",
    var price: String? = null,
    @SerialName("bought_quantity") @SerializedName("bought_quantity") var boughtQuantity: String? = null
) {
    val id: String get() = "${ingredientId}_$unit"
}

@Serializable
data class DeficitItem(
    @SerialName("ingredient_name") @SerializedName("ingredient_name") val ingredientName: String,
    @SerialName("missing_quantity") @SerializedName("missing_quantity") val missingQuantity: String,
    val unit: String
)

/** C1 - Vòng 13: cài đặt hộ gia đình cục bộ (không lưu lên server). */
@Serializable
data class HouseholdSettings(
    val householdSize: Int = 1,
    val defaultServings: Int = 2,
    val mealPeriods: List<String> = listOf("lunch", "dinner"),
    val skipDates: List<String> = emptyList(),
    val planDays: Int = 3
)
