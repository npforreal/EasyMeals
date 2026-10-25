package com.easymeals.app.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast
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
import com.easymeals.app.data.backup.BackupManager
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.ui.theme.ForestGreen

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
                    containerColor = ForestGreen.copy(alpha = 0.1f)
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
                        tint = ForestGreen,
                        modifier = Modifier.size(32.dp)
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Column {
                        Text("100% Ngoại tuyến & Riêng tư", fontWeight = FontWeight.Bold, color = ForestGreen)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "EasyMeals không yêu cầu quyền Internet. Dữ liệu của bạn được lưu hoàn toàn trên thiết bị.",
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
                                Triple("green", "Xanh lá", Color(0xFF3F6B3A)),
                                Triple("terracotta", "Cam đất", Color(0xFFA04A26)),
                                Triple("ocean", "Xanh biển", Color(0xFF285E86))
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
                                Triple("plum", "Tím mận", Color(0xFF6E396E)),
                                Triple("peach", "Hồng đào", Color(0xFF9C435A))
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
                            importError = "Dữ liệu JSON không hợp lệ: ${e.message}"
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreen)
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
    iconTint: Color = ForestGreen,
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
