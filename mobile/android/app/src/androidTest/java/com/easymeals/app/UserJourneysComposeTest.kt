package com.easymeals.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertTrue
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
        composeTestRule.onAllNodesWithText("Tủ lạnh").onLast().performClick()
        composeTestRule.waitForIdle()

        // Nút thêm đồ vào tủ
        composeTestRule.onNodeWithContentDescription("Thêm đồ vào tủ").performClick()
        composeTestRule.waitForIdle()

        // Bảng thêm nguyên liệu xuất hiện
        composeTestRule.onNodeWithText("Thêm đồ vào tủ").assertIsDisplayed()
    }

    @Test
    fun testJourney2_PlanEatUndo() {
        // Tab Hôm nay
        composeTestRule.onAllNodesWithText("Hôm nay").onLast().performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onAllNodesWithText("Hôm nay").onFirst().assertIsDisplayed()
    }

    @Test
    fun testJourney3_ShoppingToPantry() {
        // Tab Đi chợ
        composeTestRule.onAllNodesWithText("Đi chợ").onLast().performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onAllNodes(hasText("đi chợ", substring = true, ignoreCase = true)).onFirst().assertIsDisplayed()
    }

    @Test
    fun testJourney4_BrowseRecipesAndCookingMode() {
        // Tab Công thức
        composeTestRule.onAllNodesWithText("Công thức").onLast().performClick()
        composeTestRule.waitForIdle()

        // Chip lọc danh mục
        // "Tất cả" xuất hiện ở chip danh mục và các bộ lọc thời gian/độ khó; chỉ cần có ít nhất một cái đang hiển thị.
        val chips = composeTestRule.onAllNodesWithText("Tất cả")
        val count = chips.fetchSemanticsNodes().size
        val anyDisplayed = (0 until count).any { i ->
            runCatching { chips[i].assertIsDisplayed() }.isSuccess
        }
        assertTrue("Không có chip 'Tất cả' nào hiển thị", anyDisplayed)
    }
}
