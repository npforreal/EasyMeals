package com.easymeals.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.ui.screens.LeftoverOptionsRow
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Tuỳ chọn đồ ăn dư (A1 - Vòng 13): hiện đủ, toggle được và giữ selected chip đúng trên khổ hẹp 280/320/360/384dp. */
@RunWith(AndroidJUnit4::class)
class LeftoverOptionsTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun assertRowUsableAtWidth(widthDp: Dp) {
        var allow = true
        var days = 2
        composeTestRule.setContent {
            EasyMealsTheme {
                // 32.dp = lề hai bên của màn hình
                Box(Modifier.width(widthDp - 32.dp)) {
                    Column {
                        LeftoverOptionsRow(
                            allowLeftovers = allow,
                            leftoverDays = days,
                            onAllowChange = { allow = it },
                            onDaysChange = { days = it }
                        )
                    }
                }
            }
        }
        // Nhãn bật/tắt và cả 3 chip 1/2/3 ngày phải hiển thị đủ, không bị cắt
        composeTestRule.onNodeWithText("Cho dùng lại đồ ăn dư").assertIsDisplayed()
        for (d in 1..3) {
            composeTestRule.onNodeWithText("$d ngày").assertIsDisplayed()
        }
        composeTestRule.onNodeWithText("2 ngày").assertIsSelected()

        // Bấm chip 1 ngày -> callback nhận 1; bấm chip 3 ngày -> callback nhận 3
        composeTestRule.onNodeWithText("1 ngày").performClick()
        assertEquals(1, days)
        composeTestRule.onNodeWithText("3 ngày").performClick()
        assertEquals(3, days)
    }

    @Test fun leftoverOptionsUsableAt280dp() = assertRowUsableAtWidth(280.dp)
    @Test fun leftoverOptionsUsableAt320dp() = assertRowUsableAtWidth(320.dp)
    @Test fun leftoverOptionsUsableAt360dp() = assertRowUsableAtWidth(360.dp)
    @Test fun leftoverOptionsUsableAt384dp() = assertRowUsableAtWidth(384.dp)
}
