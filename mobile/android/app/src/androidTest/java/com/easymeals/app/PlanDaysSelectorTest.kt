package com.easymeals.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.ui.screens.PlanDaysSelector
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Chip 1–7 phải hiện đủ và bấm được trên mọi khổ màn hình hẹp (lỗi thật: chip 7 bị cắt trên Samsung A17). */
@RunWith(AndroidJUnit4::class)
class PlanDaysSelectorTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun assertAllChipsReachable(widthDp: Dp) {
        var picked = 0
        composeTestRule.setContent {
            EasyMealsTheme {
                // 32.dp = lề hai bên của màn hình
                Box(Modifier.width(widthDp - 32.dp)) {
                    PlanDaysSelector(selected = 3, onSelect = { picked = it })
                }
            }
        }
        for (d in 1..7) {
            composeTestRule.onNodeWithText("$d").assertIsDisplayed()
        }
        composeTestRule.onNodeWithText("7").performClick()
        assert(picked == 7) { "Bấm chip 7 phải chọn 7 ngày, nhưng nhận $picked" }
    }

    @Test fun allSevenChipsVisibleAt280dp() = assertAllChipsReachable(280.dp)
    @Test fun allSevenChipsVisibleAt320dp() = assertAllChipsReachable(320.dp)
    @Test fun allSevenChipsVisibleAt360dp() = assertAllChipsReachable(360.dp)
    @Test fun allSevenChipsVisibleAt384dp() = assertAllChipsReachable(384.dp)
}
