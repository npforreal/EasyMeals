package com.easymeals.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.domain.model.Ingredient
import com.easymeals.app.domain.model.Recipe

/** Chế độ chọn món thủ công cho một bữa chưa ăn (D2b): thêm món mới hoặc đổi một món cùng nhóm. */
sealed class RecipePickerMode {
    object Add : RecipePickerMode()
    data class Swap(val oldDishId: String, val category: String) : RecipePickerMode()
}

/**
 * Hộp thoại tìm và chọn món. Món chứa nguyên liệu người dùng đã đặt cần tránh có nhãn cảnh báo
 * và chỉ được chọn sau khi xác nhận "Vẫn thêm". [onPick] chỉ gọi sau khi đã qua bước xác nhận
 * (tham số thứ hai là cờ confirmedAvoidance).
 */
@Composable
internal fun RecipePickerDialog(
    mode: RecipePickerMode,
    recipes: List<Recipe>,
    ingredients: List<Ingredient>,
    avoidedIngredientIds: Set<String>,
    onPick: (Recipe, Boolean) -> Unit,
    onDismiss: () -> Unit
) {
    var query by remember { mutableStateOf("") }
    var pending by remember { mutableStateOf<Pair<Recipe, String>?>(null) }

    fun violationName(recipe: Recipe): String? {
        val hit = recipe.ingredients.firstOrNull { it.ingredientId in avoidedIngredientIds } ?: return null
        return ingredients.firstOrNull { it.id == hit.ingredientId }?.name ?: "nguyên liệu đã chọn"
    }

    val q = query.trim().lowercase()
    val candidates = recipes.filter { recipe ->
        (mode !is RecipePickerMode.Swap || recipe.category == mode.category) &&
            (q.isEmpty() || recipe.name.lowercase().contains(q))
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (mode is RecipePickerMode.Swap) "Đổi món" else "Thêm món") },
        text = {
            Column {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    label = { Text("Tìm tên món") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyColumn(modifier = Modifier.heightIn(max = 320.dp)) {
                    items(candidates, key = { it.id }) { recipe ->
                        val violation = violationName(recipe)
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 48.dp)
                                .clickable {
                                    if (violation != null) pending = recipe to violation
                                    else onPick(recipe, false)
                                }
                                .padding(vertical = 8.dp)
                        ) {
                            Text(recipe.name, fontSize = 15.sp)
                            if (violation != null) {
                                Text(
                                    "Chứa nguyên liệu bạn cần tránh",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.error
                                )
                            }
                        }
                        HorizontalDivider()
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { Text("Huỷ") } }
    )

    pending?.let { (recipe, name) ->
        AlertDialog(
            onDismissRequest = { pending = null },
            title = { Text("Món này cần tránh") },
            text = { Text("Món này chứa $name mà bạn đã đặt cần tránh. Vẫn thêm?") },
            confirmButton = {
                TextButton(onClick = { pending = null; onPick(recipe, true) }) { Text("Vẫn thêm") }
            },
            dismissButton = { TextButton(onClick = { pending = null }) { Text("Huỷ") } }
        )
    }
}
