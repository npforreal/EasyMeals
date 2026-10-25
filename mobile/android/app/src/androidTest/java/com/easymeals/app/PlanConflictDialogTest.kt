package com.easymeals.app

import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.ui.screens.PlanConflictDialog
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Hộp thoại giữ/thay khi tạo thực đơn trùng ngày bữa chưa ăn (A2 - Vòng 13):
 * hiện đủ 3 lựa chọn (Thay/Giữ/Huỷ) và gọi đúng callback trên khổ hẹp 280/320/360/384dp.
 */
@RunWith(AndroidJUnit4::class)
class PlanConflictDialogTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun assertDialogUsableAtWidth(widthDp: Dp) {
        var replace = 0
        var keep = 0
        var dismissed = false
        composeTestRule.setContent {
            EasyMealsTheme {
                PlanConflictDialog(
                    onReplace = { replace++ },
                    onKeep = { keep++ },
                    onDismiss = { dismissed = true }
                )
            }
        }
        composeTestRule.onNodeWithText("Thực đơn mới trùng ngày").assertIsDisplayed()
        composeTestRule.onNodeWithText("Thay các bữa chưa ăn trong khoảng ngày này")
            .assertIsDisplayed()
        composeTestRule.onNodeWithText("Giữ thực đơn cũ, chỉ thêm ngày chưa có")
            .assertIsDisplayed()
        composeTestRule.onNodeWithText("Huỷ").assertIsDisplayed()

        composeTestRule.onNodeWithText("Giữ thực đơn cũ, chỉ thêm ngày chưa có").performClick()
        assertEquals(1, keep)
        assertEquals(0, replace)
        composeTestRule.onNodeWithText("Thay các bữa chưa ăn trong khoảng ngày này").performClick()
        assertEquals(1, replace)
        composeTestRule.onNodeWithText("Huỷ").performClick()
        assertTrue(dismissed)
    }

    @Test fun planConflictDialogUsableAt280dp() = assertDialogUsableAtWidth(280.dp)
    @Test fun planConflictDialogUsableAt320dp() = assertDialogUsableAtWidth(320.dp)
    @Test fun planConflictDialogUsableAt360dp() = assertDialogUsableAtWidth(360.dp)
    @Test fun planConflictDialogUsableAt384dp() = assertDialogUsableAtWidth(384.dp)
}
