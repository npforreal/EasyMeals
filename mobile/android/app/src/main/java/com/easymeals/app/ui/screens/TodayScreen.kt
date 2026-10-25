package com.easymeals.app.ui.screens

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DinnerDining
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.domain.model.DeficitItem
import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.ui.theme.GeneratedTokens
import com.easymeals.app.util.DateFormatter

private data class DeficitAlertState(
    val planId: String,
    val deficits: Map<String, DeficitItem>
)

/**
 * Hàng tuỳ chọn đồ ăn dư: bật/tắt dùng lại đồ dư và số ngày dùng lại (1-3, mặc định 2).
 * Ghép với cả hai chỗ tạo thực đơn trong TodayScreen, đọc/ghi qua AppRepository.
 */
@Composable
internal fun LeftoverOptionsRow(
    allowLeftovers: Boolean,
    leftoverDays: Int,
    onAllowChange: (Boolean) -> Unit,
    onDaysChange: (Int) -> Unit
) {
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = allowLeftovers, onCheckedChange = onAllowChange)
            Text(
                "Cho dùng lại đồ ăn dư",
                fontSize = 14.sp,
                modifier = Modifier.weight(1f)
            )
        }
        if (allowLeftovers) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(start = 16.dp)
            ) {
                Text(
                    "Dùng lại trong tối đa:",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.width(8.dp))
                for (days in GeneratedTokens.PlanLimits.LEFTOVER_MIN_DAYS..GeneratedTokens.PlanLimits.LEFTOVER_MAX_DAYS) {
                    FilterChip(
                        selected = leftoverDays == days,
                        onClick = { onDaysChange(days) },
                        label = { Text("$days ngày", fontSize = 12.sp) },
                        modifier = Modifier.padding(end = 6.dp)
                    )
                }
            }
        }
    }
}

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
    // Hộp thoại giữ/thay khi tạo thực đơn trùng ngày bữa chưa ăn (A2 - Vòng 13).
    var planConflictDays by remember { mutableStateOf<Int?>(null) }

    // A2: nếu đợt mới trùng bữa CHƯA ăn -> hỏi giữ/thay trước khi tạo; nút luôn dùng đường này.
    val onRequestGenerate: (Int) -> Unit = { days ->
        if (repository.hasUneatenOverlap(days)) {
            planConflictDays = days
        } else {
            repository.generateNewPlan(days)
        }
    }

    var selectedPlanDays by remember {
        val prefs = context.getSharedPreferences("easymeals_prefs", Context.MODE_PRIVATE)
        val saved = prefs.getInt("selected_plan_days", GeneratedTokens.PlanLimits.DEFAULT_DAYS)
        mutableIntStateOf(saved.coerceIn(GeneratedTokens.PlanLimits.MIN_DAYS, GeneratedTokens.PlanLimits.MAX_DAYS))
    }

    val onSelectDays: (Int) -> Unit = { d ->
        selectedPlanDays = d
        val prefs = context.getSharedPreferences("easymeals_prefs", Context.MODE_PRIVATE)
        prefs.edit().putInt("selected_plan_days", d).apply()
    }

    val allowLeftovers by repository.allowLeftovers.collectAsState()
    val leftoverDays by repository.leftoverDays.collectAsState()

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
                            tint = MaterialTheme.colorScheme.primary,
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
                        Spacer(modifier = Modifier.height(20.dp))
                        Text(
                            "Số ngày lập thực đơn (1–7 ngày):",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        PlanDaysSelector(
                            selected = selectedPlanDays,
                            onSelect = onSelectDays,
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                        LeftoverOptionsRow(
                            allowLeftovers = allowLeftovers,
                            leftoverDays = leftoverDays,
                            onAllowChange = { repository.setAllowLeftovers(it) },
                            onDaysChange = { repository.setLeftoverDays(it) }
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(
                            onClick = { onRequestGenerate(selectedPlanDays) },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Lên thực đơn $selectedPlanDays ngày", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            } else {
                val lastPlanDate = mealPlans.maxOfOrNull { it.plannedFor } ?: ""
                val expiringFreshLots = remember(pantryLots, lastPlanDate) {
                    if (lastPlanDate.isBlank()) emptyList()
                    else pantryLots.filter { lot ->
                        !lot.expiresAt.isNullOrBlank() && lot.expiresAt <= lastPlanDate
                    }
                }

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    if (expiringFreshLots.isNotEmpty()) {
                        item {
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    val names = expiringFreshLots.joinToString(", ") { "${it.ingredientName} (${DateFormatter.formatDateVN(it.expiresAt!!)})" }
                                    Text(
                                        "Đồ tươi sắp hết hạn trong thực đơn: $names. Hãy ưu tiên nấu sớm hoặc gia hạn trong tủ.",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onErrorContainer
                                    )
                                }
                            }
                        }
                    }

                    item {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text("Lên đợt thực đơn mới:", fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                Spacer(modifier = Modifier.height(6.dp))
                                PlanDaysSelector(selected = selectedPlanDays, onSelect = onSelectDays)
                                Spacer(modifier = Modifier.height(4.dp))
                                LeftoverOptionsRow(
                                    allowLeftovers = allowLeftovers,
                                    leftoverDays = leftoverDays,
                                    onAllowChange = { repository.setAllowLeftovers(it) },
                                    onDaysChange = { repository.setLeftoverDays(it) }
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Button(
                                    onClick = { onRequestGenerate(selectedPlanDays) },
                                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                                ) {
                                    Icon(Icons.Default.AutoAwesome, contentDescription = null)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Lên thực đơn $selectedPlanDays ngày", fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }

                    items(mealPlans, key = { it.id }) { plan ->
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

        planConflictDays?.let { days ->
            PlanConflictDialog(
                onReplace = {
                    repository.generateNewPlan(days, mergeMode = "replace")
                    planConflictDays = null
                },
                onKeep = {
                    repository.generateNewPlan(days, mergeMode = "keep")
                    planConflictDays = null
                },
                onDismiss = { planConflictDays = null }
            )
        }
    }
}

/**
 * Hộp thoại giữ/thay khi tạo thực đơn trùng ngày với bữa CHƯA ăn (A2 - Vòng 13).
 * Bữa đã ăn luôn được giữ cùng lịch sử kho, không có lựa chọn nào xoá chúng.
 * Tách composable `internal` để instrumented test dựng riêng ở các khổ hẹp dp.
 */
@Composable
internal fun PlanConflictDialog(
    onReplace: () -> Unit,
    onKeep: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Thực đơn mới trùng ngày") },
        text = {
            Text(
                "Thực đơn mới trùng ngày với bữa chưa ăn. " +
                    "Bạn muốn xử lý thế nào? Các bữa đã ăn luôn được giữ cùng lịch sử kho."
            )
        },
        confirmButton = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onReplace,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Thay các bữa chưa ăn trong khoảng ngày này")
                }
                OutlinedButton(
                    onClick = onKeep,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Giữ thực đơn cũ, chỉ thêm ngày chưa có")
                }
                TextButton(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Huỷ")
                }
            }
        },
        dismissButton = null
    )
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
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        DateFormatter.formatRelativeDate(plan.plannedFor),
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                }
                if (plan.eatenAt != null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Đã ăn", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
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
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Đã ăn (Trừ kho)", fontWeight = FontWeight.Bold)
                }
            } else {
                OutlinedButton(
                    onClick = onUndo,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Hoàn tác bữa ăn này", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}


/**
 * Hàng chọn số ngày lập thực đơn (MIN_DAYS..MAX_DAYS). Mỗi nút chia đều chiều ngang (weight) nên
 * luôn đủ 7 nút trên màn hẹp, thay vì chip rộng cố định bị cắt mất nút cuối.
 */
@Composable
fun PlanDaysSelector(
    selected: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier.fillMaxWidth()
    ) {
        (GeneratedTokens.PlanLimits.MIN_DAYS..GeneratedTokens.PlanLimits.MAX_DAYS).forEach { d ->
            val isSelected = selected == d
            val shape = RoundedCornerShape(10.dp)
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 48.dp)
                    .clip(shape)
                    .background(
                        if (isSelected) MaterialTheme.colorScheme.primaryContainer
                        else MaterialTheme.colorScheme.surface
                    )
                    .border(
                        1.dp,
                        if (isSelected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.outline,
                        shape
                    )
                    .selectable(
                        selected = isSelected,
                        role = Role.RadioButton,
                        onClick = { onSelect(d) }
                    )
            ) {
                Text(
                    "$d",
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                    color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer
                    else MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}
