package com.easymeals.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.domain.model.Ingredient
import com.easymeals.app.domain.model.PantryLot
import com.easymeals.app.ui.screens.AddPantryBottomSheet
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PantrySaveButtonTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun testPantrySaveButtonJourneyOnDevice() {
        // Tab Tủ lạnh (click tab ở bottom bar)
        composeTestRule.onAllNodesWithText("Tủ lạnh").onLast().performClick()
        composeTestRule.waitForIdle()

        // Mở bảng thêm đồ vào tủ
        composeTestRule.onNodeWithContentDescription("Thêm đồ vào tủ").performClick()
        composeTestRule.waitForIdle()

        // Bảng hiện
        composeTestRule.onNodeWithText("Thêm đồ vào tủ").assertIsDisplayed()

        // Tìm và chọn "Gạo"
        composeTestRule.onNodeWithText("Tìm nguyên liệu (ba chỉ, đậu bắp...)").performTextInput("Gạo")
        composeTestRule.waitForIdle()

        // Chọn item Gạo chính xác
        composeTestRule.onAllNodes(hasText("Gạo", substring = false)).onFirst().performClick()
        composeTestRule.waitForIdle()

        // Khẳng định nút "Lưu một chạm" luôn nhìn thấy NGAY LẬP TỨC mà KHÔNG CẦN CUỘN
        composeTestRule.onNodeWithText("Lưu một chạm").assertIsDisplayed()

        // Nhập vào ô Số lượng (kích hoạt bàn phím ảo)
        composeTestRule.onNodeWithText("Số lượng").performTextClearance()
        composeTestRule.onNodeWithText("Số lượng").performTextInput("600")
        composeTestRule.waitForIdle()

        // Khẳng định nút "Lưu một chạm" vẫn hiển thị trên bàn phím
        composeTestRule.onNodeWithText("Lưu một chạm").assertIsDisplayed()

        // Bấm nút Lưu một chạm
        composeTestRule.onNodeWithText("Lưu một chạm").performClick()
        composeTestRule.waitForIdle()

        // Khẳng định Gạo đã xuất hiện trong danh sách Tủ lạnh
        composeTestRule.onAllNodes(hasText("Gạo", substring = true)).onFirst().assertIsDisplayed()
    }
}
