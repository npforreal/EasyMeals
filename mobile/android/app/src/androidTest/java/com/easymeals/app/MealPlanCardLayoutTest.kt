package com.easymeals.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.PlannedDish
import com.easymeals.app.ui.screens.MealPlanCard
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Hồi quy: trên máy thật, hàng món bị ép nên "Xem công thức" xếp dọc từng chữ và nút Đổi/Bỏ mất.
 * Các nút Thêm/Đổi/Bỏ phải hiển thị, đủ vùng chạm và gọi đúng callback ở khổ hẹp 280–384dp.
 */
@RunWith(AndroidJUnit4::class)
class MealPlanCardLayoutTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun check(widthDp: Dp) {
        val plan = MealPlan(
            plannedFor = "2026-10-27", mealPeriod = "lunch",
            dishes = mutableListOf(
                PlannedDish(
                    id = "d1", recipeId = "r1", recipeName = "Canh khoai mỡ nấu tôm thịt", category = "canh",
                    selectionReason = "Chọn món thay thế, bổ sung vào danh sách đi chợ"
                )
            )
        )
        var swapped: Pair<String, String>? = null
        var removed: String? = null
        var added = false
        composeTestRule.setContent {
            EasyMealsTheme {
                Box(Modifier.width(widthDp)) {
                    MealPlanCard(
                        plan = plan, onNotesChange = {}, onViewRecipe = { _, _ -> }, onEat = {}, onUndo = {}, onRegenerate = {},
                        onAddDish = { added = true },
                        onSwapDish = { id, cat -> swapped = id to cat },
                        onRemoveDish = { removed = it }
                    )
                }
            }
        }
        composeTestRule.onNodeWithText("Xem công thức").assertIsDisplayed()
        composeTestRule.onNodeWithContentDescription("Đổi món Canh khoai mỡ nấu tôm thịt").assertIsDisplayed().assertHeightIsAtLeast(48.dp)
        composeTestRule.onNodeWithContentDescription("Bỏ món Canh khoai mỡ nấu tôm thịt").assertIsDisplayed().assertHeightIsAtLeast(48.dp)
        composeTestRule.onNodeWithText("Thêm món").assertIsDisplayed()
        composeTestRule.onNodeWithContentDescription("Đổi món Canh khoai mỡ nấu tôm thịt").performClick()
        composeTestRule.onNodeWithContentDescription("Bỏ món Canh khoai mỡ nấu tôm thịt").performClick()
        composeTestRule.onNodeWithText("Thêm món").performClick()
        assertEquals("d1" to "canh", swapped)
        assertEquals("d1", removed)
        assertEquals(true, added)
    }

    @Test fun mealCardUsableAt280dp() = check(280.dp)
    @Test fun mealCardUsableAt320dp() = check(320.dp)
    @Test fun mealCardUsableAt360dp() = check(360.dp)
    @Test fun mealCardUsableAt384dp() = check(384.dp)
}
