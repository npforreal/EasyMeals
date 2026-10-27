package com.easymeals.app.ui.screens

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.easymeals.app.data.backup.BackupManager
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.data.notifications.ReminderScheduler
import com.easymeals.app.ui.theme.GeneratedTokens

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(repository: AppRepository) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var showWipeConfirm by remember { mutableStateOf(false) }
    var showImportDialog by remember { mutableStateOf(false) }
    var importJsonText by remember { mutableStateOf("") }
    var importError by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Cài đặt", fontWeight = FontWeight.Bold) },
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
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Privacy Banner
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.Security,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(32.dp)
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text("100% Ngoại tuyến & Riêng tư", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "EasyMeals không yêu cầu quyền Internet. Dữ liệu của bạn được lưu hoàn toàn trên thiết bị. Ứng dụng chỉ xin quyền thông báo khi bạn bật nhắc việc.",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Section: Appearance & Color Palette (F1)
            val currentThemeMode by repository.themeMode.collectAsState()
            val currentPalette by repository.palette.collectAsState()

            Text(
                "GIAO DIỆN & MÀU SẮC",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Chế độ hiển thị", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf(
                            "system" to "Hệ thống",
                            "light" to "Sáng",
                            "dark" to "Tối"
                        ).forEach { (mode, label) ->
                            FilterChip(
                                selected = currentThemeMode == mode,
                                onClick = { repository.setThemeMode(mode) },
                                label = { Text(label) },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = MaterialTheme.colorScheme.primary,
                                    selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                )
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                    HorizontalDivider()
                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Bảng màu nhấn", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            listOf(
                                Triple("green", "Xanh lá", GeneratedTokens.Palettes.Green.light.primary),
                                Triple("terracotta", "Cam đất", GeneratedTokens.Palettes.Terracotta.light.primary),
                                Triple("ocean", "Xanh biển", GeneratedTokens.Palettes.Ocean.light.primary)
                            ).forEach { (id, label, color) ->
                                FilterChip(
                                    selected = currentPalette == id,
                                    onClick = { repository.setPalette(id) },
                                    leadingIcon = {
                                        Surface(
                                            modifier = Modifier.size(14.dp),
                                            shape = RoundedCornerShape(7.dp),
                                            color = color
                                        ) {}
                                    },
                                    label = { Text(label) },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = MaterialTheme.colorScheme.primary,
                                        selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                    )
                                )
                            }
                        }
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            listOf(
                                Triple("plum", "Tím mận", GeneratedTokens.Palettes.Plum.light.primary),
                                Triple("peach", "Hồng đào", GeneratedTokens.Palettes.Peach.light.primary)
                            ).forEach { (id, label, color) ->
                                FilterChip(
                                    selected = currentPalette == id,
                                    onClick = { repository.setPalette(id) },
                                    leadingIcon = {
                                        Surface(
                                            modifier = Modifier.size(14.dp),
                                            shape = RoundedCornerShape(7.dp),
                                            color = color
                                        ) {}
                                    },
                                    label = { Text(label) },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = MaterialTheme.colorScheme.primary,
                                        selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                    )
                                )
                            }
                        }
                    }
                }
            }

            // Section: Đồ ăn dư (A1 - Vòng 13)
            val currentAllowLeftovers by repository.allowLeftovers.collectAsState()
            val currentLeftoverDays by repository.leftoverDays.collectAsState()

            Text(
                "ĐỒ ĂN DƯ",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 16.dp)
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Dùng lại đồ ăn dư", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Bật để thực đơn tận dụng phần dư của mẻ nấu trước, tránh lãng phí thực phẩm.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Cho phép", fontSize = 14.sp, modifier = Modifier.weight(1f))
                        Switch(
                            checked = currentAllowLeftovers,
                            onCheckedChange = { repository.setAllowLeftovers(it) }
                        )
                    }
                    if (currentAllowLeftovers) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Dùng lại trong tối đa", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            for (days in GeneratedTokens.PlanLimits.LEFTOVER_MIN_DAYS..GeneratedTokens.PlanLimits.LEFTOVER_MAX_DAYS) {
                                FilterChip(
                                    selected = currentLeftoverDays == days,
                                    onClick = { repository.setLeftoverDays(days) },
                                    label = { Text("$days ngày") },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = MaterialTheme.colorScheme.primary,
                                        selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                    )
                                )
                            }
                        }
                    }
                }
            }

            // Section: Nhắc việc (F2 - Vòng 13)
            val currentReminders by repository.remindersEnabled.collectAsState()
            var reminderNotice by remember { mutableStateOf<String?>(null) }

            val notificationPermissionLauncher = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission()
            ) { granted ->
                if (granted) {
                    repository.setRemindersEnabled(true)
                    ReminderScheduler.applySetting(context)
                    reminderNotice = "Đã bật nhắc việc lúc 9:00 sáng theo giờ máy."
                } else {
                    repository.setRemindersEnabled(false)
                    reminderNotice =
                        "Chưa được cấp quyền thông báo. Mở Cài đặt hệ thống › Ứng dụng › EasyMeals › Thông báo để bật."
                }
            }

            Text(
                "NHẮC VIỆC",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 16.dp)
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            "Nhắc hạn dùng & bữa ăn hôm nay",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f)
                        )
                        Switch(
                            checked = currentReminders,
                            onCheckedChange = { enabled ->
                                reminderNotice = null
                                if (!enabled) {
                                    repository.setRemindersEnabled(false)
                                    ReminderScheduler.applySetting(context)
                                } else {
                                    val needsPermission = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                                        ContextCompat.checkSelfPermission(
                                            context,
                                            Manifest.permission.POST_NOTIFICATIONS
                                        ) != PackageManager.PERMISSION_GRANTED
                                    if (needsPermission) {
                                        notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                                    } else {
                                        repository.setRemindersEnabled(true)
                                        ReminderScheduler.applySetting(context)
                                        reminderNotice = "Đã bật nhắc việc lúc 9:00 sáng theo giờ máy."
                                    }
                                }
                            }
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Nhắc lúc 9:00 sáng theo múi giờ của máy về lô sắp hết hạn và bữa ăn trong ngày. " +
                            "Thông báo được tạo ngay trên máy, không gửi dữ liệu đi. Hệ thống có thể gửi trễ vài phút.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (reminderNotice != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            reminderNotice!!,
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            // Section: Hộ gia đình (C1 - Vòng 13)
            val currentHouseholdSize by repository.householdSize.collectAsState()
            val currentDefaultServings by repository.defaultServings.collectAsState()
            val currentMealPeriods by repository.mealPeriods.collectAsState()
            val currentSkipDates by repository.skipDates.collectAsState()

            Text(
                "HỘ GIA ĐÌNH",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 16.dp)
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Số người ăn cùng", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = currentHouseholdSize.toString(),
                        onValueChange = {
                            val parsed = it.toIntOrNull()
                            if (parsed != null) repository.setHouseholdSize(parsed)
                        },
                        label = { Text("Số người") },
                        modifier = Modifier.fillMaxWidth().height(48.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Khẩu phần mặc định mỗi người", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = currentDefaultServings.toString(),
                        onValueChange = {
                            val parsed = it.toIntOrNull()
                            if (parsed != null) repository.setDefaultServings(parsed)
                        },
                        label = { Text("Khẩu phần") },
                        modifier = Modifier.fillMaxWidth().height(48.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Bữa cần lập mỗi ngày", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(
                            "breakfast" to "Sáng",
                            "lunch" to "Trưa",
                            "dinner" to "Tối"
                        ).forEach { (period, label) ->
                            FilterChip(
                                selected = currentMealPeriods.contains(period),
                                onClick = {
                                    val updated = if (currentMealPeriods.contains(period)) {
                                        currentMealPeriods.filter { it != period }
                                    } else {
                                        (currentMealPeriods + period)
                                    }
                                    repository.setMealPeriods(updated)
                                },
                                label = { Text(label) },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = MaterialTheme.colorScheme.primary,
                                    selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                )
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Ngày không nấu / ăn ngoài (YYYY-MM-DD, cách nhau dấu phẩy)", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = currentSkipDates.joinToString(", "),
                        onValueChange = {
                            val dates = it.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                            repository.setSkipDates(dates)
                        },
                        label = { Text("Ngày nghỉ nấu") },
                        placeholder = { Text("2026-11-01, 2026-11-02") },
                        modifier = Modifier.fillMaxWidth().height(48.dp)
                    )
                }
            }

            // Section: Lịch sử & thống kê (F1 - Vòng 13)
            val historyPlans by repository.mealPlans.collectAsState()
            val historyLots by repository.pantryLots.collectAsState()
            val historyMovements by repository.stockMovements.collectAsState()
            val history = remember(historyPlans, historyLots, historyMovements) {
                repository.historySummary()
            }

            Text(
                "LỊCH SỬ & THỐNG KÊ (30 NGÀY)",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        HistoryStat("Bữa đã nấu", history.cooked.inWindow.toString(), Modifier.weight(1f))
                        HistoryStat("Tổng bữa", history.cooked.total.toString(), Modifier.weight(1f))
                        HistoryStat("Đồ dư dùng lại", history.leftovers.reusedDishesInWindow.toString(), Modifier.weight(1f))
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider()
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        "Chi tiêu đã nhập: " +
                            if (history.spending.lotsWithPrice > 0) {
                                "${formatVnd(history.spending.inWindow)} (30 ngày)"
                            } else {
                                "chưa có dữ liệu giá"
                            },
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (history.spending.lotsMissingPrice > 0) {
                        Text(
                            "Chỉ tính ${history.spending.lotsWithPrice} lô có nhập giá; ${history.spending.lotsMissingPrice} lô chưa có giá.",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Biến động kho: ${history.stock.inWindow} lần trong 30 ngày (${history.stock.consumedCount} trừ, ${history.stock.restoredCount} cộng); tổng ${history.stock.totalMovements} bản ghi.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    if (history.cooked.meals.isEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Chưa có bữa ăn nào được đánh dấu “Đã ăn”.",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Bữa ăn gần đây", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        history.cooked.meals.take(5).forEach { meal ->
                            val period = when (meal.mealPeriod) {
                                "breakfast" -> "Sáng"
                                "lunch" -> "Trưa"
                                "dinner" -> "Tối"
                                else -> meal.mealPeriod
                            }
                            val leftover = if (meal.leftoverReuseCount > 0) " (+${meal.leftoverReuseCount} đồ dư)" else ""
                            Text(
                                "• ${formatDay(meal.plannedFor)} · $period: ${meal.dishNames.joinToString(", ").ifEmpty { "Không rõ món" }}$leftover",
                                fontSize = 12.sp,
                                modifier = Modifier.padding(top = 4.dp)
                            )
                        }
                    }

                    if (history.cooked.topRecipes.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Nấu nhiều nhất: " + history.cooked.topRecipes.joinToString(" · ") { "${it.name} ×${it.count}" },
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (history.waste.expiredLotCount > 0) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "${history.waste.expiredLotCount} lô đã quá hạn mà vẫn còn trong tủ: " +
                                history.waste.expiredLots.take(5).joinToString(", ") {
                                    "${it.ingredientName.ifEmpty { it.ingredientId }} (${it.remainingQuantity} ${it.unit})"
                                },
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.error
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Ứng dụng chưa ghi nhận lãng phí; mục quá hạn chỉ là đồ còn trong tủ, không phải số liệu lãng phí đã xác nhận.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Section: Backup & Restore
            Text(
                "SAO LƯU & KHÔI PHỤC",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column {
                    SettingsRow(
                        icon = Icons.Default.FileUpload,
                        title = "Xuất dữ liệu sao lưu",
                        subtitle = "Sao chép mã JSON vào khay nhớ tạm để chia sẻ hoặc cất giữ",
                        onClick = {
                            val json = repository.exportBackupJson()
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            val clip = ClipData.newPlainText("EasyMeals Backup", json)
                            clipboard.setPrimaryClip(clip)
                            Toast.makeText(context, "Đã sao chép sao lưu vào bộ nhớ tạm!", Toast.LENGTH_SHORT).show()
                        }
                    )
                    HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))
                    SettingsRow(
                        icon = Icons.Default.Share,
                        title = "Chia sẻ tệp sao lưu",
                        subtitle = "Gửi tệp sao lưu qua tin nhắn hoặc lưu trữ đám mây",
                        onClick = {
                            val json = repository.exportBackupJson()
                            val intent = Intent(Intent.ACTION_SEND).apply {
                                type = "application/json"
                                putExtra(Intent.EXTRA_SUBJECT, "EasyMeals_Backup.json")
                                putExtra(Intent.EXTRA_TEXT, json)
                            }
                            context.startActivity(Intent.createChooser(intent, "Chia sẻ sao lưu EasyMeals"))
                        }
                    )
                    HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))
                    SettingsRow(
                        icon = Icons.Default.FileDownload,
                        title = "Nhập dữ liệu sao lưu",
                        subtitle = "Khôi phục dữ liệu từ chuỗi JSON",
                        onClick = {
                            importJsonText = ""
                            importError = null
                            showImportDialog = true
                        }
                    )
                }
            }

            // Section: Danger Zone
            Text(
                "VÙNG NGUY HIỂM",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.error
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                SettingsRow(
                    icon = Icons.Default.DeleteForever,
                    title = "Xoá toàn bộ dữ liệu",
                    subtitle = "Xoá tủ lạnh, thực đơn, danh sách đi chợ và lịch sử",
                    iconTint = MaterialTheme.colorScheme.error,
                    onClick = { showWipeConfirm = true }
                )
            }

            // Section: About & License
            Text(
                "THÔNG TIN ỨNG DỤNG",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("EasyMeals Native Android", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Phiên bản: 2.0.0 (Native Jetpack Compose)", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Cơ sở dữ liệu món ăn: ${repository.catalogueVersion}", fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Mã nguồn mở theo giấy phép Apache-2.0. Dữ liệu món ăn theo giấy phép Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 18.sp
                    )
                }
            }
        }
    }

    // Wipe Confirm Dialog
    if (showWipeConfirm) {
        AlertDialog(
            onDismissRequest = { showWipeConfirm = false },
            title = { Text("Xác nhận xoá toàn bộ dữ liệu?") },
            text = { Text("Hành động này sẽ xoá sạch toàn bộ nguyên liệu trong tủ lạnh, thực đơn và lịch sử. Không thể hoàn tác sau khi xoá!") },
            confirmButton = {
                Button(
                    onClick = {
                        repository.wipeAllData()
                        showWipeConfirm = false
                        Toast.makeText(context, "Đã xoá toàn bộ dữ liệu ứng dụng", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Xoá sạch")
                }
            },
            dismissButton = {
                TextButton(onClick = { showWipeConfirm = false }) {
                    Text("Huỷ")
                }
            }
        )
    }

    // Import Dialog
    if (showImportDialog) {
        AlertDialog(
            onDismissRequest = { showImportDialog = false },
            title = { Text("Nhập dữ liệu sao lưu") },
            text = {
                Column {
                    Text("Dán chuỗi JSON sao lưu vào ô dưới đây:")
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = importJsonText,
                        onValueChange = {
                            importJsonText = it
                            importError = null
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(140.dp),
                        placeholder = { Text("{\"appVersion\": \"2.0.0\", ...}") },
                        isError = importError != null
                    )
                    if (importError != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(importError!!, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        try {
                            val payload = BackupManager.decode(importJsonText)
                            repository.importBackupPayload(payload, replace = true)
                            showImportDialog = false
                            Toast.makeText(context, "Khôi phục dữ liệu thành công!", Toast.LENGTH_SHORT).show()
                        } catch (e: Exception) {
                            importError = "Không nhập được bản sao lưu: ${e.message ?: "lỗi không xác định"}"
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("Nhập")
                }
            },
            dismissButton = {
                TextButton(onClick = { showImportDialog = false }) {
                    Text("Huỷ")
                }
            }
        )
    }
}

@Composable
fun SettingsRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    iconTint: Color = MaterialTheme.colorScheme.primary,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        color = Color.Transparent,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = iconTint,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    subtitle,
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Icon(
                Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@Composable
private fun HistoryStat(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            value,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        Text(label, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun formatVnd(value: Long): String {
    val grouped = value.toString().reversed().chunked(3).joinToString(".").reversed()
    return "$grouped đ"
}

/** "2026-10-27" -> "27/10/2026"; giá trị lạ được giữ nguyên. */
private fun formatDay(value: String): String {
    if (value.length < 10) return value
    val parts = value.substring(0, 10).split("-")
    return if (parts.size == 3) "${parts[2]}/${parts[1]}/${parts[0]}" else value
}
