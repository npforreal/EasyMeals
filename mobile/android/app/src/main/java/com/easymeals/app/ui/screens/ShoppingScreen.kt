package com.easymeals.app.ui.screens

import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.data.ShoppingDefaults
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.data.db.PurchaseOverride
import com.easymeals.app.domain.engine.EasyMealsEngine
import com.easymeals.app.domain.model.ShoppingItem
import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private val CATEGORY_LABELS = mapOf(
    "thit" to "Thịt tươi sống",
    "gia_cam" to "Gia cầm & trứng",
    "hai_san" to "Hải sản tươi sống",
    "trung_sua" to "Trứng & Sữa",
    "rau_cu" to "Rau tươi & nấm",
    "cu_qua" to "Củ & quả",
    "gao_bot_mi" to "Gạo, mì & bột",
    "gia_vi" to "Gia vị & phụ liệu",
    "nuoc_cham_dau" to "Nước chấm & dầu ăn",
    "khac" to "Mặt hàng khác"
)

private fun formatVnd(amountStr: String): String {
    val num = amountStr.toDoubleOrNull() ?: 0.0
    return NumberFormat.getIntegerInstance(Locale("vi", "VN")).format(num.toLong()) + " đ"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingScreen(repository: AppRepository) {
    val shoppingItems by repository.shoppingItems.collectAsState()
    val context = LocalContext.current
    var showAddDialog by remember { mutableStateOf(false) }
    var editingPriceItem by remember { mutableStateOf<ShoppingItem?>(null) }
    var showPurchaseDialog by remember { mutableStateOf(false) }

    val budget = remember(shoppingItems) { EasyMealsEngine.calculateShoppingBudget(shoppingItems) }
    val groupedItems = remember(shoppingItems) { EasyMealsEngine.groupShoppingItemsByCategory(shoppingItems) }

    fun shareList() {
        val sb = StringBuilder("DANH SÁCH ĐI CHỢ - EASYMEALS\n\n")
        groupedItems.forEach { (catKey, itemsInCat) ->
            sb.append("=== ${CATEGORY_LABELS[catKey] ?: "Mặt hàng khác"} ===\n")
            itemsInCat.forEach { item ->
                val mark = if (item.isBought) "[x]" else "[ ]"
                val priceInfo = if (!item.price.isNullOrBlank()) " (~${formatVnd(item.price!!)})" else ""
                sb.append("$mark ${item.ingredientName}: ${item.neededQuantity} ${item.unit}$priceInfo\n")
            }
            sb.append("\n")
        }
        if (budget.itemsWithPriceCount > 0) {
            sb.append("Dự toán: ${formatVnd(budget.totalEstimatedBudget)} | Đã chi: ${formatVnd(budget.totalSpent)}\n")
        }
        val sendIntent = Intent().apply {
            action = Intent.ACTION_SEND
            putExtra(Intent.EXTRA_TEXT, sb.toString())
            type = "text/plain"
        }
        val shareIntent = Intent.createChooser(sendIntent, "Chia sẻ danh sách đi chợ")
        context.startActivity(shareIntent)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Đi chợ", fontWeight = FontWeight.Bold) },
                actions = {
                    if (shoppingItems.isNotEmpty()) {
                        IconButton(onClick = { shareList() }) {
                            Icon(Icons.Default.Share, contentDescription = "Chia sẻ")
                        }
                    }
                    IconButton(onClick = { showAddDialog = true }) {
                        Icon(Icons.Default.Add, contentDescription = "Thêm món")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (shoppingItems.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ShoppingCart,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
                            modifier = Modifier.size(72.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("Danh sách đi chợ trống", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Khi lên thực đơn, nguyên liệu còn thiếu trong tủ sẽ tự động hiển thị tại đây.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                // Card Ngân sách & Chi tiêu (B4)
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "Ngân sách & Chi tiêu",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(
                                "${budget.itemsWithPriceCount}/${budget.totalItemsCount} món có giá",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text("Dự toán tổng", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    formatVnd(budget.totalEstimatedBudget),
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text("Đã chi", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    formatVnd(budget.totalSpent),
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }

                LazyColumn(
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    groupedItems.forEach { (catKey, itemsInCat) ->
                        item(key = "header_$catKey") {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 12.dp, bottom = 4.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        CATEGORY_LABELS[catKey] ?: "Mặt hàng khác",
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 13.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Text(
                                        "${itemsInCat.size} món",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }

                        items(itemsInCat, key = { it.id }) { item ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { repository.toggleShoppingItem(item.id) }
                                    .padding(vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    if (item.isBought) Icons.Default.CheckCircle else Icons.Default.RadioButtonUnchecked,
                                    contentDescription = null,
                                    tint = if (item.isBought) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        item.ingredientName,
                                        fontSize = 15.sp,
                                        fontWeight = FontWeight.Medium,
                                        textDecoration = if (item.isBought) TextDecoration.LineThrough else null,
                                        color = if (item.isBought) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface
                                    )
                                    if (item.dishNames.isNotEmpty()) {
                                        Text(
                                            "Cho món: ${item.dishNames.joinToString(", ")}",
                                            fontSize = 11.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                                Column(
                                    horizontalAlignment = Alignment.End,
                                    modifier = Modifier.padding(horizontal = 6.dp)
                                ) {
                                    Text(
                                        "${item.neededQuantity} ${item.unit}",
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 14.sp,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = if (!item.price.isNullOrBlank()) formatVnd(item.price!!) else "+ Giá",
                                        fontSize = 12.sp,
                                        color = if (!item.price.isNullOrBlank()) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.clickable { editingPriceItem = item }
                                    )
                                }
                                IconButton(
                                    onClick = { repository.deleteShoppingItem(item.id) },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.Default.Delete,
                                        contentDescription = "Xoá",
                                        tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                            }
                            HorizontalDivider()
                        }
                    }
                }

                val boughtCount = shoppingItems.count { it.isBought }
                if (boughtCount > 0) {
                    Button(
                        onClick = { showPurchaseDialog = true },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp)
                    ) {
                        Text("Cho $boughtCount món đã mua vào tủ lạnh", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        if (showPurchaseDialog) {
            PurchaseConfirmDialog(
                boughtItems = shoppingItems.filter { it.isBought },
                ingredientCategories = shoppingItems.filter { it.isBought }.associate {
                    it.id to repository.categoryOf(it.ingredientId)
                },
                onConfirm = { overrides ->
                    repository.bulkAddBoughtToPantry(overrides)
                    showPurchaseDialog = false
                },
                onDismiss = { showPurchaseDialog = false }
            )
        }

        // Dialog cập nhật giá từng món (B4)
        editingPriceItem?.let { item ->
            var priceInput by remember(item) { mutableStateOf(item.price ?: "") }
            AlertDialog(
                onDismissRequest = { editingPriceItem = null },
                title = { Text("Giá món: ${item.ingredientName}") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Nhập giá thực tế người dùng chi trả (VNĐ):", fontSize = 13.sp)
                        OutlinedTextField(
                            value = priceInput,
                            onValueChange = { priceInput = it.filter { ch -> ch.isDigit() } },
                            label = { Text("Đơn giá (VNĐ)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            repository.updateShoppingItemPrice(item.id, priceInput)
                            editingPriceItem = null
                        }
                    ) {
                        Text("Lưu giá")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { editingPriceItem = null }) {
                        Text("Đóng")
                    }
                }
            )
        }

        // Dialog Thêm món tự do (B3)
        if (showAddDialog) {
            var name by remember { mutableStateOf("") }
            var qty by remember { mutableStateOf("200") }
            var unit by remember { mutableStateOf("g") }
            var selectedCategory by remember { mutableStateOf("khac") }
            var priceInput by remember { mutableStateOf("") }
            var categoryExpanded by remember { mutableStateOf(false) }

            AlertDialog(
                onDismissRequest = { showAddDialog = false },
                title = { Text("Thêm món tự do") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        OutlinedTextField(
                            value = name,
                            onValueChange = { name = it },
                            label = { Text("Tên nguyên liệu") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = qty,
                                onValueChange = { qty = it },
                                label = { Text("Số lượng") },
                                modifier = Modifier.weight(1f)
                            )
                            OutlinedTextField(
                                value = unit,
                                onValueChange = { unit = it },
                                label = { Text("Đơn vị") },
                                modifier = Modifier.width(90.dp)
                            )
                        }
                        // Quầy hàng
                        Box(modifier = Modifier.fillMaxWidth()) {
                            OutlinedButton(
                                onClick = { categoryExpanded = true },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Quầy: ${CATEGORY_LABELS[selectedCategory] ?: "Khác"}")
                            }
                            DropdownMenu(
                                expanded = categoryExpanded,
                                onDismissRequest = { categoryExpanded = false }
                            ) {
                                CATEGORY_LABELS.forEach { (catKey, catLabel) ->
                                    DropdownMenuItem(
                                        text = { Text(catLabel) },
                                        onClick = {
                                            selectedCategory = catKey
                                            categoryExpanded = false
                                        }
                                    )
                                }
                            }
                        }
                        // Đơn giá tuỳ chọn
                        OutlinedTextField(
                            value = priceInput,
                            onValueChange = { priceInput = it.filter { ch -> ch.isDigit() } },
                            label = { Text("Đơn giá VNĐ (tuỳ chọn)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            if (name.isNotBlank()) {
                                repository.addCustomShoppingItem(
                                    name = name,
                                    quantity = qty,
                                    unit = unit,
                                    category = selectedCategory,
                                    price = priceInput
                                )
                                showAddDialog = false
                            }
                        }
                    ) { Text("Thêm") }
                },
                dismissButton = {
                    TextButton(onClick = { showAddDialog = false }) { Text("Huỷ") }
                }
            )
        }
    }
}

/**
 * A4 - Vòng 13: hộp thoại xác nhận "mua vào tủ" cho các món đã tích chọn.
 * Mỗi mục cho phép nhập LƯỢNG THỰC MUA (mặc định = ước tính) và HẠN DÙNG
 * (mặc định theo nhóm nguyên liệu, format yyyy-MM-dd).
 * Tách composable `internal` để instrumented test dựng riêng ở các khổ hẹp dp.
 */
@Composable
internal fun PurchaseConfirmDialog(
    boughtItems: List<ShoppingItem>,
    ingredientCategories: Map<String, String?>,
    onConfirm: (List<PurchaseOverride>) -> Unit,
    onDismiss: () -> Unit
) {
    var quantities by remember { mutableStateOf(boughtItems.associate { it.id to it.neededQuantity }) }
    var expiries by remember {
        val today = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE)
        mutableStateOf(
            boughtItems.associate {
                it.id to ShoppingDefaults.expiryDate(ingredientCategories[it.id], LocalDate.now())
            }
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Xác nhận mua vào tủ") },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(boughtItems, key = { it.id }) { item ->
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            "${item.ingredientName}: ước tính ${item.neededQuantity} ${item.unit}",
                            fontWeight = FontWeight.Medium
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = quantities[item.id] ?: item.neededQuantity,
                                onValueChange = { v -> quantities = quantities + (item.id to v) },
                                label = { Text("Thực mua (${item.unit})") },
                                singleLine = true,
                                modifier = Modifier.weight(1f)
                            )
                            OutlinedTextField(
                                value = expiries[item.id] ?: "",
                                onValueChange = { v -> expiries = expiries + (item.id to v) },
                                label = { Text("Hạn dùng (yyyy-mm-dd)") },
                                singleLine = true,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = {
                        onConfirm(
                            boughtItems.map { item ->
                                PurchaseOverride(
                                    itemId = item.id,
                                    actualQuantity = quantities[item.id] ?: item.neededQuantity,
                                    expiresAt = expiries[item.id] ?: ""
                                )
                            }
                        )
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Cho ${boughtItems.size} món vào tủ lạnh")
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
