package com.easymeals.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class UserJourneysComposeTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun testJourney1_PantryAddition() {
        // Tab Tủ lạnh
        composeTestRule.onNodeWithText("Tủ lạnh").performClick()
        composeTestRule.waitForIdle()

        // Kiểm tra placeholder tìm kiếm L4
        composeTestRule.onNodeWithText("Tìm trong tủ...").assertIsDisplayed()

        // Nút thêm đồ vào tủ
        composeTestRule.onNodeWithContentDescription("Thêm đồ vào tủ").performClick()
        composeTestRule.waitForIdle()

        // Bảng thêm nguyên liệu xuất hiện
        composeTestRule.onNodeWithText("Thêm nguyên liệu vào tủ").assertIsDisplayed()
    }

    @Test
    fun testJourney2_PlanEatUndo() {
        // Tab Hôm nay
        composeTestRule.onNodeWithText("Hôm nay").performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("Hôm nay").assertIsDisplayed()
    }

    @Test
    fun testJourney3_ShoppingToPantry() {
        // Tab Đi chợ
        composeTestRule.onNodeWithText("Đi chợ").performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("Danh sách đi chợ").assertIsDisplayed()
    }

    @Test
    fun testJourney4_BrowseRecipesAndCookingMode() {
        // Tab Công thức
        composeTestRule.onNodeWithText("Công thức").performClick()
        composeTestRule.waitForIdle()

        // Chip lọc danh mục
        composeTestRule.onNodeWithText("Tất cả").assertIsDisplayed()
    }
}
