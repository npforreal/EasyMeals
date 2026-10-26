package com.easymeals.app.ui.screens

import android.app.Activity
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.view.WindowManager
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.domain.engine.ExactDecimal
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.ui.theme.GeneratedTokens

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecipesScreen(repository: AppRepository) {
    val context = LocalContext.current
    val recipePreferences = remember { context.getSharedPreferences("recipe_preferences", android.content.Context.MODE_PRIVATE) }
    val recipes by repository.recipes.collectAsState()
    val ingredients by repository.ingredients.collectAsState()
    val pantryLots by repository.pantryLots.collectAsState()
    var searchQuery by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("Tất cả") }
    var dietaryFilter by remember { mutableStateOf(recipePreferences.getString("dietary_filter", "") ?: "") }
    var showAvoidDialog by remember { mutableStateOf(false) }
    var showPreferredDialog by remember { mutableStateOf(false) }
    var avoidedIngredientIds by remember { mutableStateOf(recipePreferences.getStringSet("avoided_ingredient_ids", emptySet()).orEmpty()) }
    var preferredIngredientIds by remember { mutableStateOf(recipePreferences.getStringSet("preferred_ingredient_ids", emptySet()).orEmpty()) }
    var maxSpice by remember {
        mutableStateOf(recipePreferences.getString("max_spice", "")?.toIntOrNull())
    }
    var showSpiceMenu by remember { mutableStateOf(false) }
    var selectedRecipe by remember { mutableStateOf<Recipe?>(null) }
    var isCookingMode by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

    BackHandler(enabled = isCookingMode) {
        isCookingMode = false
    }

    BackHandler(enabled = selectedRecipe != null && !isCookingMode) {
        selectedRecipe = null
    }

    val categories = remember(recipes) {
        val cats = recipes.map { it.category }.distinct().sorted()
        listOf("Tất cả") + cats
    }

    val filteredRecipes = remember(recipes, searchQuery, selectedCategory, dietaryFilter, avoidedIngredientIds, preferredIngredientIds, maxSpice) {
        recipes.filter { recipe ->
            val catLabel = com.easymeals.app.ui.theme.GeneratedTokens.Labels.dish_categories[recipe.category] ?: recipe.category
            val matchCat = selectedCategory == "Tất cả" || recipe.category == selectedCategory
            val matchQuery = searchQuery.isBlank() ||
                    CatalogueLoader.matches(recipe.name, searchQuery) ||
                    CatalogueLoader.matches(recipe.category, searchQuery) ||
                    CatalogueLoader.matches(catLabel, searchQuery)
            val matchDiet = dietaryFilter.isEmpty() || (
                    recipe.dietaryStatus == dietaryFilter &&
                            !recipe.dietarySourceUrl.isNullOrBlank() &&
                            !recipe.dietaryVerifiedAt.isNullOrBlank()
                    )
            val matchAvoid = recipe.ingredients.none { it.ingredientId in avoidedIngredientIds }
            val matchSpice = maxSpice == null || (
                    recipe.spiceLevel != null && recipe.spiceLevel <= maxSpice!! &&
                            !recipe.spiceSourceUrl.isNullOrBlank() && !recipe.spiceVerifiedAt.isNullOrBlank()
                    )
            matchCat && matchQuery && matchDiet && matchAvoid && matchSpice
        }.sortedByDescending { recipe -> recipe.ingredients.count { it.ingredientId in preferredIngredientIds } }
    }

    if (isCookingMode && selectedRecipe != null) {
        CookingModeScreen(
            recipe = selectedRecipe!!,
            onClose = { isCookingMode = false },
            onDone = {
                isCookingMode = false
                selectedRecipe = null
            }
        )
        return
    }

    if (selectedRecipe != null) {
        RecipeDetailScreen(
            recipe = selectedRecipe!!,
            initialServings = selectedRecipe!!.servings,
            pantryLots = pantryLots,
            conversions = repository.conversions,
            onBack = { selectedRecipe = null },
            onStartCooking = { isCookingMode = true }
        )
        return
    }

    if (showAvoidDialog) {
        AlertDialog(
            onDismissRequest = { showAvoidDialog = false },
            title = { Text("Dị ứng / nguyên liệu cần tránh") },
            text = {
                LazyColumn(modifier = Modifier.heightIn(max = 420.dp)) {
                    items(ingredients, key = { it.id }) { ingredient ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(
                                checked = ingredient.id in avoidedIngredientIds,
                                onCheckedChange = { checked ->
                                    val updated = avoidedIngredientIds.toMutableSet().apply {
                                        if (checked) add(ingredient.id) else remove(ingredient.id)
                                    }.toSet()
                                    avoidedIngredientIds = updated
                                    recipePreferences.edit().putStringSet("avoided_ingredient_ids", updated).apply()
                                }
                            )
                            Text(ingredient.name)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showAvoidDialog = false }) { Text("Xong") } }
        )
    }
    if (showPreferredDialog) {
        AlertDialog(
            onDismissRequest = { showPreferredDialog = false },
            title = { Text("Nguyên liệu ưa thích") },
            text = {
                LazyColumn(modifier = Modifier.heightIn(max = 420.dp)) {
                    items(ingredients, key = { it.id }) { ingredient ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(
                                checked = ingredient.id in preferredIngredientIds,
                                onCheckedChange = { checked ->
                                    val updated = preferredIngredientIds.toMutableSet().apply {
                                        if (checked) add(ingredient.id) else remove(ingredient.id)
                                    }.toSet()
                                    preferredIngredientIds = updated
                                    recipePreferences.edit().putStringSet("preferred_ingredient_ids", updated).apply()
                                }
                            )
                            Text(ingredient.name)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showPreferredDialog = false }) { Text("Xong") } }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Kho công thức", fontWeight = FontWeight.Bold) },
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
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Chế độ ăn đã xác minh", style = MaterialTheme.typography.labelMedium)
                TextButton(onClick = { showAvoidDialog = true }) {
                    Text("Tránh nguyên liệu (${avoidedIngredientIds.size})")
                }
                TextButton(onClick = { showPreferredDialog = true }) {
                    Text("Ưa thích (${preferredIngredientIds.size})")
                }
                Box {
                    TextButton(onClick = { showSpiceMenu = true }) {
                        Text("Cay tối đa: ${maxSpice?.toString() ?: "Không giới hạn"}")
                    }
                    DropdownMenu(expanded = showSpiceMenu, onDismissRequest = { showSpiceMenu = false }) {
                        (listOf(null) + (0..5).toList()).forEach { level ->
                            DropdownMenuItem(
                                text = { Text(level?.toString() ?: "Không giới hạn") },
                                onClick = {
                                    maxSpice = level
                                    recipePreferences.edit().putString("max_spice", level?.toString() ?: "").apply()
                                    showSpiceMenu = false
                                }
                            )
                        }
                    }
                }
                FilterChip(
                    selected = dietaryFilter == "vegetarian",
                    onClick = {
                        dietaryFilter = if (dietaryFilter == "vegetarian") "" else "vegetarian"
                        recipePreferences.edit().putString("dietary_filter", dietaryFilter).apply()
                    },
                    label = { Text("Chay") }
                )
                FilterChip(
                    selected = dietaryFilter == "vegan",
                    onClick = {
                        dietaryFilter = if (dietaryFilter == "vegan") "" else "vegan"
                        recipePreferences.edit().putString("dietary_filter", dietaryFilter).apply()
                    },
                    label = { Text("Thuần chay") }
                )
            }
            Text(
                text = "Nguyên liệu tránh được lọc theo ID. Món thiếu xác minh không được coi là phù hợp; danh mục không chứng nhận an toàn dị ứng hoặc nhiễm chéo.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
            )
            // Search field
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text("Tìm theo tên món, danh mục...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(Icons.Default.Clear, contentDescription = "Xoá tìm kiếm")
                        }
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(12.dp)
            )

            // Category Chips
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(categories) { cat ->
                    val label = if (cat == "Tất cả") "Tất cả" else (com.easymeals.app.ui.theme.GeneratedTokens.Labels.dish_categories[cat] ?: cat)
                    FilterChip(
                        selected = selectedCategory == cat,
                        onClick = { selectedCategory = cat },
                        label = { Text(label) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = MaterialTheme.colorScheme.primary,
                            selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                        )
                    )
                }
            }

            // Results count
            Text(
                text = if (filteredRecipes.isEmpty() && dietaryFilter.isNotEmpty()) {
                    "Chưa có món nào được xác minh cho chế độ này."
                } else "${filteredRecipes.size} món ăn chuẩn vị Việt",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
            )

            // Recipe List
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(filteredRecipes, key = { it.id }) { recipe ->
                    RecipeCard(
                        recipe = recipe,
                        onClick = { selectedRecipe = recipe }
                    )
                }
            }
        }
    }
}

@Composable
fun RecipeCard(
    recipe: Recipe,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = recipe.name,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f)
                )
                val catLabel = com.easymeals.app.ui.theme.GeneratedTokens.Labels.dish_categories[recipe.category] ?: recipe.category
                Badge(
                    containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f),
                    contentColor = MaterialTheme.colorScheme.primary
                ) {
                    Text(
                        text = catLabel,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.Group,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        "${recipe.servings} người",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.MenuBook,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        "${recipe.ingredients.size} nguyên liệu",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.ListAlt,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        "${recipe.instructions.size} bước",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecipeDetailScreen(
    recipe: Recipe,
    initialServings: Int = recipe.servings,
    pantryLots: List<com.easymeals.app.domain.model.PantryLot> = emptyList(),
    conversions: List<com.easymeals.app.domain.model.Conversion>? = null,
    onBack: () -> Unit,
    onStartCooking: () -> Unit
) {
    var servings by remember { mutableIntStateOf(initialServings) }
    val factor = remember(servings, recipe.servings) {
        ExactDecimal(servings) / ExactDecimal(recipe.servings)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(recipe.name, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        bottomBar = {
            Surface(
                tonalElevation = 8.dp,
                shadowElevation = 8.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Button(
                    onClick = onStartCooking,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Bật Chế độ nấu", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Servings Stepper
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Khẩu phần ăn", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            Text(
                                "Tự động chia tỉ lệ nguyên liệu",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            FilledTonalIconButton(
                                onClick = { if (servings > 1) servings-- },
                                enabled = servings > 1
                            ) {
                                Icon(Icons.Default.Remove, contentDescription = "Giảm")
                            }
                            Text(
                                text = "$servings",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 16.dp)
                            )
                            FilledTonalIconButton(
                                onClick = { if (servings < 20) servings++ },
                                enabled = servings < 20
                            ) {
                                Icon(Icons.Default.Add, contentDescription = "Tăng")
                            }
                        }
                    }
                }
            }

            // Ingredients Section
            item {
                Text("Nguyên liệu", fontWeight = FontWeight.Bold, fontSize = 18.sp)
            }

            items(recipe.ingredients) { ing ->
                val baseQty = ExactDecimal(ing.quantity)
                val scaledQty = (baseQty * factor)
                val available = if (pantryLots.isNotEmpty()) {
                    com.easymeals.app.domain.engine.EasyMealsEngine.getTotalIngredientStock(
                        pantryLots,
                        ing.ingredientId,
                        ing.unit,
                        conversions
                    )
                } else null

                val isEnough = available != null && available >= scaledQty
                val isPartial = available != null && available > ExactDecimal.ZERO && available < scaledQty

                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "• ${ing.ingredientName}",
                            fontSize = 15.sp,
                            modifier = Modifier.weight(1f)
                        )
                        Text(
                            text = "$scaledQty ${ing.unit}",
                            fontWeight = FontWeight.SemiBold,
                            color = if (isEnough) MaterialTheme.colorScheme.primary else if (available != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                        )
                    }
                    if (available != null) {
                        Row(
                            modifier = Modifier.padding(start = 12.dp, top = 2.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            if (isEnough) {
                                Text(
                                    "✓ Trong tủ có sẵn: $available ${ing.unit}",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            } else if (isPartial) {
                                val missing = scaledQty - available
                                Text(
                                    "⚠ Có $available, còn thiếu $missing ${ing.unit}",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.error
                                )
                            } else {
                                Text(
                                    "✗ Chưa có trong tủ",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.error
                                )
                            }
                        }
                    }
                }
            }

            // Instructions Section
            if (recipe.instructions.isNotEmpty()) {
                item {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Hướng dẫn các bước", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                }

                items(recipe.instructions.indices.toList()) { index ->
                    val step = recipe.instructions[index]
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(28.dp)
                                .clip(RoundedCornerShape(14.dp))
                                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                "${index + 1}",
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 13.sp
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = step,
                            fontSize = 15.sp,
                            modifier = Modifier.weight(1f),
                            lineHeight = 22.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CookingModeScreen(
    recipe: Recipe,
    onClose: () -> Unit,
    onDone: () -> Unit
) {
    val context = LocalContext.current
    var currentStep by remember { mutableIntStateOf(0) }
    val totalSteps = recipe.instructions.size

    // Keep screen on during cooking mode
    DisposableEffect(Unit) {
        val window = (context as? Activity)?.window
        window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onClose) {
                    Icon(Icons.Default.Close, contentDescription = "Thoát")
                }
                Text(
                    "CHẾ ĐỘ NẤU",
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.secondary
                )
                Text(
                    if (totalSteps > 0) "${currentStep + 1} / $totalSteps" else "1/1",
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Progress Indicator
            LinearProgressIndicator(
                progress = {
                    if (totalSteps > 0) (currentStep + 1).toFloat() / totalSteps.toFloat() else 1f
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(RoundedCornerShape(4.dp)),
                color = MaterialTheme.colorScheme.primary
            )

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                recipe.name,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Step Content Box
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(16.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    if (totalSteps > 0 && currentStep < totalSteps) {
                        Text(
                            text = recipe.instructions[currentStep],
                            fontSize = 20.sp,
                            lineHeight = 32.sp,
                            fontWeight = FontWeight.Medium,
                            textAlign = TextAlign.Center
                        )
                    } else {
                        Text(
                            text = "Thực hiện theo kinh nghiệm nấu món ${recipe.name}",
                            fontSize = 18.sp,
                            textAlign = TextAlign.Center
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Navigation Controls
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedButton(
                    onClick = { if (currentStep > 0) currentStep-- },
                    enabled = currentStep > 0,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Bước trước")
                }

                if (currentStep < totalSteps - 1) {
                    Button(
                        onClick = { currentStep++ },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Bước tiếp")
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null)
                    }
                } else {
                    Button(
                        onClick = {
                            val vibrator = context.getSystemService(Vibrator::class.java)
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                vibrator?.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
                            }
                            onDone()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Check, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Nấu xong")
                    }
                }
            }
        }
    }
}
