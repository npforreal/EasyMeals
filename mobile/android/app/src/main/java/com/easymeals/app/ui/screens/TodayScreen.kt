package com.easymeals.app.ui.screens

import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DinnerDining
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.domain.model.DeficitItem
import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.ui.theme.ForestGreen
import com.easymeals.app.ui.theme.GeneratedTokens
import com.easymeals.app.util.DateFormatter

private data class DeficitAlertState(
    val planId: String,
    val deficits: Map<String, DeficitItem>
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(repository: AppRepository) {
    val mealPlans by repository.mealPlans.collectAsState()
    val recipes by repository.recipes.collectAsState()
    val pantryLots by repository.pantryLots.collectAsState()
    val context = LocalContext.current

    var viewingRecipe by remember { mutableStateOf<Recipe?>(null) }
    var viewingServings by remember { mutableIntStateOf(2) }
    var isCookingMode by remember { mutableStateOf(false) }
    var deficitAlert by remember { mutableStateOf<DeficitAlertState?>(null) }

    BackHandler(enabled = isCookingMode) {
        isCookingMode = false
    }

    BackHandler(enabled = viewingRecipe != null && !isCookingMode) {
        viewingRecipe = null
    }

    if (isCookingMode && viewingRecipe != null) {
        CookingModeScreen(
            recipe = viewingRecipe!!,
            onClose = { isCookingMode = false },
            onDone = {
                isCookingMode = false
                viewingRecipe = null
            }
        )
        return
    }

    if (viewingRecipe != null) {
        RecipeDetailScreen(
            recipe = viewingRecipe!!,
            initialServings = viewingServings,
            pantryLots = pantryLots,
            conversions = repository.conversions,
            onBack = { viewingRecipe = null },
            onStartCooking = { isCookingMode = true }
        )
        return
    }

    fun vibrate() {
        try {
            val vibrator = context.getSystemService(Vibrator::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(50, VibrationEffect.DEFAULT_AMPLITUDE))
            }
        } catch (_: Exception) {}
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Hôm nay", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (mealPlans.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(32.dp)
                    ) {
                        Icon(
                            Icons.Default.DinnerDining,
                            contentDescription = null,
                            tint = ForestGreen,
                            modifier = Modifier.size(80.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("Chưa có thực đơn", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Lập thực đơn thông minh dựa trên đồ có sẵn trong tủ, không trùng món và tận dụng thức ăn thừa.",
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(24.dp))
                        Button(
                            onClick = { repository.generateNewPlan(3) },
                            colors = ButtonDefaults.buttonColors(containerColor = ForestGreen),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Lên thực đơn 3 ngày ngay", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(mealPlans.take(4), key = { it.id }) { plan ->
                        MealPlanCard(
                            plan = plan,
                            onViewRecipe = { recipeId, servings ->
                                val found = recipes.find { it.id == recipeId }
                                if (found != null) {
                                    viewingRecipe = found
                                    viewingServings = servings
                                }
                            },
                            onEat = {
                                val (canEat, deficits) = repository.checkMealStock(plan.id)
                                if (canEat) {
                                    vibrate()
                                    repository.eatMeal(plan.id, allowPartial = false)
                                } else {
                                    deficitAlert = DeficitAlertState(plan.id, deficits)
                                }
                            },
                            onUndo = {
                                repository.undoLastEatMeal()
                            }
                        )
                    }
                }
            }
        }

        deficitAlert?.let { alert ->
            AlertDialog(
                onDismissRequest = { deficitAlert = null },
                title = { Text("Không đủ nguyên liệu") },
                text = {
                    Column {
                        Text("Bữa ăn còn thiếu các nguyên liệu sau trong kho:")
                        Spacer(modifier = Modifier.height(8.dp))
                        for (d in alert.deficits.values) {
                            Text(
                                "• ${d.ingredientName}: thiếu ${d.missingQuantity} ${d.unit}",
                                fontWeight = FontWeight.Medium,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Bạn muốn xử lý thế nào?")
                    }
                },
                confirmButton = {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                repository.addDeficitsToShoppingList(alert.deficits.values)
                                deficitAlert = null
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Thêm vào danh sách đi chợ")
                        }
                        OutlinedButton(
                            onClick = {
                                vibrate()
                                repository.eatMeal(alert.planId, allowPartial = true)
                                deficitAlert = null
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Vẫn đánh dấu đã ăn (trừ phần đang có)")
                        }
                        TextButton(
                            onClick = { deficitAlert = null },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Huỷ")
                        }
                    }
                },
                dismissButton = null
            )
        }
    }
}

@Composable
fun MealPlanCard(
    plan: MealPlan,
    onViewRecipe: (String, Int) -> Unit,
    onEat: () -> Unit,
    onUndo: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    val periodLabel = GeneratedTokens.Labels.meal_periods[plan.mealPeriod]?.uppercase()
                        ?: (if (plan.mealPeriod == "lunch") "BỮA TRƯA" else "BỮA TỐI")
                    Text(
                        periodLabel,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreen
                    )
                    Text(
                        DateFormatter.formatRelativeDate(plan.plannedFor),
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                }
                if (plan.eatenAt != null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF388E3C), modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Đã ăn", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF388E3C))
                    }
                }
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            plan.dishes.forEach { dish ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = dish.recipeName,
                        fontSize = 15.sp,
                        modifier = Modifier
                            .weight(1f)
                            .padding(end = 8.dp)
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        if (dish.isLeftover) {
                            SuggestionChip(
                                onClick = {},
                                label = { Text("Ăn lại", fontSize = 11.sp) }
                            )
                        }
                        TextButton(
                            onClick = { onViewRecipe(dish.recipeId, dish.servings) },
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                        ) {
                            Icon(Icons.Default.MenuBook, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Xem công thức", fontSize = 12.sp)
                        }
                    }
                }
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

            if (plan.eatenAt == null) {
                Button(
                    onClick = onEat,
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreen),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Đã ăn (Trừ kho)", fontWeight = FontWeight.Bold)
                }
            } else {
                OutlinedButton(
                    onClick = onUndo,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Hoàn tác bữa ăn này", color = ForestGreen, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
