package com.easymeals.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onLast
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.domain.model.Ingredient
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.domain.model.RecipeIngredient
import com.easymeals.app.ui.screens.RecipePickerDialog
import com.easymeals.app.ui.screens.RecipePickerMode
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * D2b: chọn món thủ công. Món chứa nguyên liệu cần tránh phải hỏi xác nhận; Huỷ thì không chọn,
 * "Vẫn thêm" thì gọi onPick với confirmedAvoidance = true.
 */
@RunWith(AndroidJUnit4::class)
class RecipePickerDialogTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private val safe = Recipe(id = "r-safe", name = "Canh rau muống", category = "canh")
    private val risky = Recipe(
        id = "r-risky", name = "Canh khoai mỡ", category = "canh",
        ingredients = listOf(RecipeIngredient(ingredientId = "ing-om", ingredientName = "Rau om", quantity = "10", unit = "g"))
    )
    private val otherCategory = Recipe(id = "r-man", name = "Thịt kho", category = "man")
    private val ingredients = listOf(Ingredient(id = "ing-om", name = "Rau om", normalizedName = "rau om", category = "rau", defaultUnit = "g"))

    private var picked: Pair<String, Boolean>? = null
    private var dismissed = false

    private fun show(mode: RecipePickerMode) {
        picked = null
        dismissed = false
        composeTestRule.setContent {
            EasyMealsTheme {
                RecipePickerDialog(
                    mode = mode,
                    recipes = listOf(safe, risky, otherCategory),
                    ingredients = ingredients,
                    avoidedIngredientIds = setOf("ing-om"),
                    onPick = { r, confirmed -> picked = r.id to confirmed },
                    onDismiss = { dismissed = true }
                )
            }
        }
    }

    @Test
    fun safeRecipeIsPickedWithoutConfirmation() {
        show(RecipePickerMode.Add)
        composeTestRule.onNodeWithText("Canh rau muống").performClick()
        assertEquals("r-safe" to false, picked)
    }

    @Test
    fun riskyRecipeShowsWarningLabelAndAsksConfirmation() {
        show(RecipePickerMode.Add)
        composeTestRule.onNodeWithText("Chứa nguyên liệu bạn cần tránh").assertIsDisplayed()
        composeTestRule.onNodeWithText("Canh khoai mỡ").performClick()
        composeTestRule.onNodeWithText("Món này chứa Rau om mà bạn đã đặt cần tránh. Vẫn thêm?").assertIsDisplayed()
        assertNull(picked)
    }

    @Test
    fun cancelOnConfirmationDoesNotPick() {
        show(RecipePickerMode.Add)
        composeTestRule.onNodeWithText("Canh khoai mỡ").performClick()
        // Hai nút "Huỷ": hộp thoại xác nhận nằm trên cùng.
        composeTestRule.onAllNodesWithText("Huỷ").onLast().performClick()
        composeTestRule.waitForIdle()
        assertNull(picked)
        composeTestRule.onNodeWithText("Thêm món").assertIsDisplayed()
    }

    @Test
    fun confirmingPicksWithConfirmedAvoidance() {
        show(RecipePickerMode.Add)
        composeTestRule.onNodeWithText("Canh khoai mỡ").performClick()
        composeTestRule.onNodeWithText("Vẫn thêm").performClick()
        assertEquals("r-risky" to true, picked)
    }

    @Test
    fun swapModeOnlyListsSameCategoryAndSearchFilters() {
        show(RecipePickerMode.Swap(oldDishId = "d1", category = "canh"))
        composeTestRule.onNodeWithText("Đổi món").assertIsDisplayed()
        composeTestRule.onNodeWithText("Thịt kho").assertDoesNotExist()
        composeTestRule.onNodeWithText("Tìm tên món").performTextInput("rau")
        composeTestRule.onNodeWithText("Canh rau muống").assertIsDisplayed()
        composeTestRule.onNodeWithText("Canh khoai mỡ").assertDoesNotExist()
    }
}
