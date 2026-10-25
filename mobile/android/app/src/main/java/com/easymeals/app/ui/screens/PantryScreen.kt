package com.easymeals.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Kitchen
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.domain.model.Ingredient
import com.easymeals.app.domain.model.PantryLot
import com.easymeals.app.ui.theme.GeneratedTokens
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import com.easymeals.app.util.DateFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PantryScreen(repository: AppRepository) {
    val pantryLots by repository.pantryLots.collectAsState()
    val ingredients by repository.ingredients.collectAsState()
    var showAddSheet by remember { mutableStateOf(false) }
    var searchQuery by remember { mutableStateOf("") }

    val filteredLots = remember(pantryLots, searchQuery) {
        if (searchQuery.isBlank()) pantryLots
        else pantryLots.filter { CatalogueLoader.matches(it.ingredientName, searchQuery) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Tủ lạnh", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddSheet = true },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Thêm đồ vào tủ")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (pantryLots.isNotEmpty()) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Tìm trong tủ") },
                    leadingIcon = {
                        Icon(
                            Icons.Default.Search,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Clear, contentDescription = "Xoá tìm kiếm")
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    singleLine = true
                )
            }

            if (pantryLots.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(32.dp)
                    ) {
                        Icon(
                            Icons.Default.Kitchen,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
                            modifier = Modifier.size(72.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(
                            "Tủ lạnh đang trống",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Bấm nút dấu cộng bên dưới để thêm nguyên liệu vào tủ nhanh chóng.",
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(filteredLots, key = { it.id }) { lot ->
                        PantryLotItem(lot = lot, onDelete = { repository.removePantryLot(lot.id) })
                    }
                }
            }
        }
    }

    if (showAddSheet) {
        AddPantryBottomSheet(
            ingredients = ingredients,
            recentLots = pantryLots,
            onDismiss = { showAddSheet = false },
            onSave = { ing, qty, unit, exp ->
                repository.addPantryLot(
                    ingredientId = ing.id,
                    ingredientName = ing.name,
                    quantity = qty,
                    unit = unit,
                    expiresAt = exp
                )
                showAddSheet = false
            }
        )
    }
}

@Composable
fun PantryLotItem(lot: PantryLot, onDelete: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(lot.ingredientName, fontWeight = FontWeight.SemiBold, fontSize = 17.sp)
                lot.expiresAt?.let { exp ->
                    val status = DateFormatter.formatExpiryStatus(exp)
                    if (status != null) {
                        Text(
                            "Hạn dùng: ${status.text}",
                            fontSize = 12.sp,
                            color = if (status.isWarning) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Text(
                            "Hạn dùng: ${DateFormatter.formatDateVN(exp)}",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
            Text(
                "${lot.remainingQuantity} ${lot.unit}",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.width(12.dp))
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = "Xoá", tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

fun sensibleDefaultQuantity(ing: Ingredient): String {
    val unit = ing.defaultUnit ?: "g"
    val cat = ing.category ?: "khac"
    val name = ing.name.lowercase()
    return when (unit) {
        "piece" -> when {
            name.contains("trứng") -> "6"
            name.contains("đậu hũ") || name.contains("tàu hũ") -> "2"
            else -> "1"
        }
        "kg", "l" -> "1"
        "ml" -> if (cat == "nuoc_cham_dau") "100" else "200"
        else -> when (cat) {
            "thit", "gia_cam", "hai_san" -> "400"
            "rau_cu", "cu_qua" -> "300"
            "gao_bot_mi" -> "500"
            "gia_vi" -> "30"
            "nuoc_cham_dau" -> "100"
            else -> "200"
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddPantryBottomSheet(
    ingredients: List<Ingredient>,
    recentLots: List<PantryLot>,
    onDismiss: () -> Unit,
    onSave: (Ingredient, String, String, String?) -> Unit
) {
    var searchIngText by remember { mutableStateOf("") }
    var selectedIng by remember { mutableStateOf<Ingredient?>(null) }
    var quantityText by remember { mutableStateOf("200") }
    var unit by remember { mutableStateOf("g") }
    var selectedExpiryDays by remember { mutableStateOf<Int?>(3) }

    val recentIngs = remember(recentLots, ingredients) {
        val names = recentLots.take(6).map { it.ingredientName }.toSet()
        ingredients.filter { names.contains(it.name) }
    }

    val filtered = remember(searchIngText, ingredients) {
        if (searchIngText.isBlank()) ingredients.take(15)
        else ingredients.filter { CatalogueLoader.matches(it.name, searchIngText) }.take(20)
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxHeight(0.9f)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .padding(horizontal = 24.dp)
                .padding(bottom = 16.dp)
        ) {
            Text("Thêm đồ vào tủ", fontSize = 20.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(16.dp))

            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
            ) {
                if (selectedIng == null) {
                    OutlinedTextField(
                        value = searchIngText,
                        onValueChange = { searchIngText = it },
                        label = { Text("Tìm nguyên liệu (ba chỉ, đậu bắp...)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    if (recentIngs.isNotEmpty() && searchIngText.isBlank()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Mua gần đây:", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            recentIngs.forEach { ing ->
                                SuggestionChip(
                                    onClick = {
                                        selectedIng = ing
                                        unit = ing.defaultUnit ?: "g"
                                        quantityText = sensibleDefaultQuantity(ing)
                                        selectedExpiryDays = GeneratedTokens.Labels.default_expiry_days[ing.category ?: "khac"]?.let {
                                            if (it == "None") null else it.toInt()
                                        }
                                    },
                                    label = { Text(ing.name) }
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(max = 240.dp)
                            .verticalScroll(rememberScrollState())
                    ) {
                        filtered.forEach { ing ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        selectedIng = ing
                                        unit = ing.defaultUnit ?: "g"
                                        quantityText = sensibleDefaultQuantity(ing)
                                        selectedExpiryDays = GeneratedTokens.Labels.default_expiry_days[ing.category ?: "khac"]?.let {
                                            if (it == "None") null else it.toInt()
                                        }
                                    }
                                    .padding(vertical = 10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(ing.name, fontWeight = FontWeight.Medium)
                                Text(categoryLabel(ing.category), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            HorizontalDivider()
                        }
                    }
                } else {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            selectedIng!!.name,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        TextButton(onClick = { selectedIng = null }) {
                            Text("Đổi")
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedTextField(
                        value = quantityText,
                        onValueChange = { quantityText = it },
                        label = { Text("Số lượng") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = unit,
                        onValueChange = { unit = it },
                        label = { Text("Đơn vị") },
                        modifier = Modifier.width(100.dp)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))
                Text("Hạn sử dụng:", fontSize = 13.sp, fontWeight = FontWeight.Medium)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf(Pair("3 ngày", 3), Pair("1 tuần", 7), Pair("2 tuần", 14), Pair("Không hạn", null)).forEach { (lbl, days) ->
                        FilterChip(
                            selected = selectedExpiryDays == days,
                            onClick = { selectedExpiryDays = days },
                            label = { Text(lbl) }
                        )
                    }
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            // Sticky Save Button at Bottom
            Button(
                onClick = {
                    val exp = selectedExpiryDays?.let { java.time.LocalDate.now().plusDays(it.toLong()).toString() }
                    selectedIng?.let { onSave(it, quantityText, unit, exp) }
                },
                enabled = selectedIng != null && quantityText.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("Lưu một chạm", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

/** Nhãn nhóm nguyên liệu bằng tiếng Việt dùng chung từ GeneratedTokens. */
internal fun categoryLabel(category: String?): String {
    if (category.isNullOrBlank()) return ""
    return GeneratedTokens.Labels.ingredient_categories[category] ?: category
}
