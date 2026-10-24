package com.easymeals.app.ui.screens

import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DinnerDining
import androidx.compose.material.icons.filled.AutoAwesome
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
import com.easymeals.app.domain.engine.InsufficientStockException
import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.ui.theme.ForestGreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(repository: AppRepository) {
    val mealPlans by repository.mealPlans.collectAsState()
    val context = LocalContext.current
    var errorMessage by remember { mutableStateOf<String?>(null) }

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
                            onEat = {
                                try {
                                    val vibrator = context.getSystemService(Vibrator::class.java)
                                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                        vibrator?.vibrate(VibrationEffect.createOneShot(50, VibrationEffect.DEFAULT_AMPLITUDE))
                                    }
                                    repository.eatMeal(plan.id)
                                } catch (e: InsufficientStockException) {
                                    errorMessage = e.message
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

        errorMessage?.let { msg ->
            AlertDialog(
                onDismissRequest = { errorMessage = null },
                confirmButton = {
                    TextButton(onClick = { errorMessage = null }) { Text("Đã hiểu") }
                },
                title = { Text("Không đủ nguyên liệu") },
                text = { Text(msg) }
            )
        }
    }
}

@Composable
fun MealPlanCard(
    plan: MealPlan,
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
                    Text(
                        if (plan.mealPeriod == "lunch") "BỮA TRƯA" else "BỮA TỐI",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreen
                    )
                    Text(plan.plannedFor, fontWeight = FontWeight.Bold, fontSize = 16.sp)
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
                    Text(dish.recipeName, fontSize = 15.sp)
                    if (dish.isLeftover) {
                        SuggestionChip(
                            onClick = {},
                            label = { Text("Ăn lại", fontSize = 11.sp) }
                        )
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
