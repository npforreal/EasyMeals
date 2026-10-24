package com.easymeals.app.ui.screens

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
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
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.ui.theme.ForestGreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingScreen(repository: AppRepository) {
    val shoppingItems by repository.shoppingItems.collectAsState()
    val context = LocalContext.current
    var showAddDialog by remember { mutableStateOf(false) }

    fun shareList() {
        val sb = StringBuilder("DANH SÁCH ĐI CHỢ - EASYMEALS\n\n")
        shoppingItems.forEach { item ->
            val mark = if (item.isBought) "[x]" else "[ ]"
            sb.append("$mark ${item.ingredientName}: ${item.neededQuantity} ${item.unit}\n")
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
                            tint = ForestGreen.copy(alpha = 0.6f),
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
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(16.dp)
                ) {
                    items(shoppingItems, key = { it.id }) { item ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { repository.toggleShoppingItem(item.id) }
                                .padding(vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                if (item.isBought) Icons.Default.CheckCircle else Icons.Default.RadioButtonUnchecked,
                                contentDescription = null,
                                tint = if (item.isBought) ForestGreen else Color.Gray
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    item.ingredientName,
                                    fontSize = 16.sp,
                                    textDecoration = if (item.isBought) TextDecoration.LineThrough else null,
                                    color = if (item.isBought) Color.Gray else MaterialTheme.colorScheme.onSurface
                                )
                                if (item.dishNames.isNotEmpty()) {
                                    Text(
                                        "Cho món: ${item.dishNames.joinToString(", ")}",
                                        fontSize = 12.sp,
                                        color = Color.Gray
                                    )
                                }
                            }
                            Text(
                                "${item.neededQuantity} ${item.unit}",
                                fontWeight = FontWeight.Bold,
                                color = ForestGreen
                            )
                        }
                        HorizontalDivider()
                    }
                }

                val boughtCount = shoppingItems.count { it.isBought }
                if (boughtCount > 0) {
                    Button(
                        onClick = { repository.bulkAddBoughtToPantry() },
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreen),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp)
                    ) {
                        Text("Cho $boughtCount món đã mua vào tủ lạnh", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        if (showAddDialog) {
            var name by remember { mutableStateOf("") }
            var qty by remember { mutableStateOf("200") }
            var unit by remember { mutableStateOf("g") }

            AlertDialog(
                onDismissRequest = { showAddDialog = false },
                title = { Text("Thêm món cần mua") },
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
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            if (name.isNotBlank()) {
                                repository.addCustomShoppingItem(name, qty, unit)
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
