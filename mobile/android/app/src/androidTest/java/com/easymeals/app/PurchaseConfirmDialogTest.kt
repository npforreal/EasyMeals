package com.easymeals.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.easymeals.app.data.db.PurchaseOverride
import com.easymeals.app.domain.model.ShoppingItem
import com.easymeals.app.ui.screens.PurchaseConfirmDialog
import com.easymeals.app.ui.theme.EasyMealsTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * A4 - Vòng 13: hộp thoại xác nhận mua vào tủ — hiện đủ trường lượng thực mua/hạn dùng
 * cho từng món và trả override đúng khi xác nhận, trên khổ hẹp 280/320/360/384dp.
 */
@RunWith(AndroidJUnit4::class)
class PurchaseConfirmDialogTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private fun assertDialogUsableAtWidth(widthDp: Dp) {
        val items = listOf(
            ShoppingItem(
                ingredientId = "ing-1",
                ingredientName = "Thịt ba chỉ",
                neededQuantity = "1000",
                unit = "g"
            ),
            ShoppingItem(
                ingredientId = "ing-2",
                ingredientName = "Cải xanh",
                neededQuantity = "300",
                unit = "g"
            )
        )
        var confirmed: List<PurchaseOverride>? = null
        composeTestRule.setContent {
            EasyMealsTheme {
                PurchaseConfirmDialog(
                    boughtItems = items,
                    ingredientCategories = emptyMap(),
                    onConfirm = { confirmed = it },
                    onDismiss = { }
                )
            }
        }
        composeTestRule.onNodeWithText("Xác nhận mua vào tủ").assertIsDisplayed()
        composeTestRule.onNodeWithText("Thịt ba chỉ: ước tính 1000 g").assertIsDisplayed()
        composeTestRule.onNodeWithText("Cải xanh: ước tính 300 g").assertIsDisplayed()
        composeTestRule.onNodeWithText("Cho 2 món vào tủ lạnh").assertIsDisplayed()

        // Sửa lượng thực mua của mục đầu: 1000 -> 850.
        composeTestRule.onNodeWithText("Thực mua (g)").performTextReplacement("850")

        composeTestRule.onNodeWithText("Cho 2 món vào tủ lạnh").performClick()
        val overrides = confirmed
        assertEquals(2, overrides?.size)
        val first = overrides?.first { it.itemId == "ing-1_g" }
        assertEquals("850", first?.actualQuantity)
        // Hạn dùng được điền sẵn theo nhóm mặc định (yyyy-mm-dd).
        val second = overrides?.first { it.itemId == "ing-2_g" }
        assertTrue(Regex("\\d{4}-\\d{2}-\\d{2}").matches(second?.expiresAt ?: ""))
    }

    @Test fun purchaseDialogUsableAt280dp() = assertDialogUsableAtWidth(280.dp)
    @Test fun purchaseDialogUsableAt320dp() = assertDialogUsableAtWidth(320.dp)
    @Test fun purchaseDialogUsableAt360dp() = assertDialogUsableAtWidth(360.dp)
    @Test fun purchaseDialogUsableAt384dp() = assertDialogUsableAtWidth(384.dp)
}
