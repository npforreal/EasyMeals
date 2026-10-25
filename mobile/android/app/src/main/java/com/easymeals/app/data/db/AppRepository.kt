package com.easymeals.app.data.db

import android.content.Context
import com.easymeals.app.data.backup.BackupManager
import com.easymeals.app.data.backup.BackupPayload
import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.domain.engine.EasyMealsEngine
import com.easymeals.app.domain.model.*
import com.easymeals.app.ui.theme.GeneratedTokens
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.UUID

class AppRepository(private val context: Context) {

    private val gson = Gson()
    private val storageFile = File(context.filesDir, "easymeals_local_state.json")

    private val _ingredients = MutableStateFlow<List<Ingredient>>(emptyList())
    val ingredients: StateFlow<List<Ingredient>> = _ingredients.asStateFlow()

    private val _recipes = MutableStateFlow<List<Recipe>>(emptyList())
    val recipes: StateFlow<List<Recipe>> = _recipes.asStateFlow()

    private val _pantryLots = MutableStateFlow<List<PantryLot>>(emptyList())
    val pantryLots: StateFlow<List<PantryLot>> = _pantryLots.asStateFlow()

    private val _mealPlans = MutableStateFlow<List<MealPlan>>(emptyList())
    val mealPlans: StateFlow<List<MealPlan>> = _mealPlans.asStateFlow()

    private val _shoppingItems = MutableStateFlow<List<ShoppingItem>>(emptyList())
    val shoppingItems: StateFlow<List<ShoppingItem>> = _shoppingItems.asStateFlow()

    private val _stockMovements = MutableStateFlow<List<StockMovement>>(emptyList())

    private val _undoMessage = MutableStateFlow<String?>(null)
    val undoMessage: StateFlow<String?> = _undoMessage.asStateFlow()

    private val _catalogueError = MutableStateFlow<String?>(null)
    val catalogueError: StateFlow<String?> = _catalogueError.asStateFlow()

    private val prefs = context.getSharedPreferences("easymeals_prefs", Context.MODE_PRIVATE)

    private val _themeMode = MutableStateFlow(prefs.getString("theme_mode", "system") ?: "system")
    val themeMode: StateFlow<String> = _themeMode.asStateFlow()

    private val _palette = MutableStateFlow(prefs.getString("theme_palette", "green") ?: "green")
    val palette: StateFlow<String> = _palette.asStateFlow()

    // Tuỳ chọn đồ ăn dư: bật/tắt và số ngày dùng lại (1-3, mặc định 2) theo quyết định chủ dự án.
    private val _allowLeftovers = MutableStateFlow(prefs.getBoolean("allow_leftovers", true))
    val allowLeftovers: StateFlow<Boolean> = _allowLeftovers.asStateFlow()

    private val _leftoverDays = MutableStateFlow(
        prefs.getInt("leftover_days", GeneratedTokens.PlanLimits.LEFTOVER_DEFAULT_DAYS)
            .coerceIn(GeneratedTokens.PlanLimits.LEFTOVER_MIN_DAYS, GeneratedTokens.PlanLimits.LEFTOVER_MAX_DAYS)
    )
    val leftoverDays: StateFlow<Int> = _leftoverDays.asStateFlow()

    fun setAllowLeftovers(enabled: Boolean) {
        _allowLeftovers.value = enabled
        prefs.edit().putBoolean("allow_leftovers", enabled).apply()
    }

    fun setLeftoverDays(days: Int) {
        val bounded = days.coerceIn(GeneratedTokens.PlanLimits.LEFTOVER_MIN_DAYS, GeneratedTokens.PlanLimits.LEFTOVER_MAX_DAYS)
        _leftoverDays.value = bounded
        prefs.edit().putInt("leftover_days", bounded).apply()
    }

    fun setThemeMode(mode: String) {
        _themeMode.value = mode
        prefs.edit().putString("theme_mode", mode).apply()
    }

    fun setPalette(paletteName: String) {
        _palette.value = paletteName
        prefs.edit().putString("theme_palette", paletteName).apply()
    }

    // Phải khai báo trước khối init: Kotlin chạy initializer theo thứ tự, khai báo sau sẽ ghi đè giá trị đã nạp.
    var conversions: List<com.easymeals.app.domain.model.Conversion> = emptyList()
        private set

    private var lastActionPlanId: String? = null
    var catalogueVersion: String = "2026.10.26"
        private set

    init {
        loadCatalogue()
        loadPersistedState()
    }

    fun retryLoadCatalogue() {
        loadCatalogue()
    }

    private fun loadCatalogue() {
        val bundle = CatalogueLoader.loadBundledCatalogue(context)
        if (bundle != null) {
            _ingredients.value = bundle.ingredients
            _recipes.value = bundle.recipes
            conversions = bundle.conversions
            catalogueVersion = bundle.version ?: catalogueVersion
            _catalogueError.value = null
        } else {
            _catalogueError.value = CatalogueLoader.lastError ?: "Không thể nạp danh mục món ăn"
        }
    }

    fun addPantryLot(
        ingredientId: String,
        ingredientName: String,
        quantity: String,
        unit: String,
        expiresAt: String? = null
    ) {
        val lot = PantryLot(
            ingredientId = ingredientId,
            ingredientName = ingredientName,
            remainingQuantity = quantity,
            purchasedQuantity = quantity,
            unit = unit,
            purchasedAt = LocalDate.now().toString(),
            expiresAt = expiresAt
        )
        val current = _pantryLots.value.toMutableList()
        current.add(0, lot)
        _pantryLots.value = current
        persistState()
    }

    fun removePantryLot(id: String) {
        _pantryLots.value = _pantryLots.value.filter { it.id != id }
        persistState()
    }

    /** Gia hạn hạn sử dụng cho lô nguyên liệu đồ tươi trong tủ (mặc định +3 ngày). */
    fun extendPantryLotExpiry(id: String, daysToAdd: Int = 3) {
        val current = _pantryLots.value.toMutableList()
        val index = current.indexOfFirst { it.id == id }
        if (index != -1) {
            val old = current[index]
            val baseDate = if (!old.expiresAt.isNullOrBlank()) {
                try {
                    java.time.LocalDate.parse(old.expiresAt)
                } catch (_: Exception) {
                    java.time.LocalDate.now()
                }
            } else {
                java.time.LocalDate.now()
            }
            val newExp = baseDate.plusDays(daysToAdd.toLong()).toString()
            current[index] = old.copy(expiresAt = newExp)
            _pantryLots.value = current
            persistState()
        }
    }

    fun checkMealStock(planId: String): Pair<Boolean, Map<String, DeficitItem>> {
        val plan = _mealPlans.value.find { it.id == planId } ?: return Pair(true, emptyMap())
        val allDeficits = mutableMapOf<String, DeficitItem>()

        // Collect requirements for all non-leftover dishes in the plan
        for (dish in plan.dishes) {
            if (dish.isLeftover) continue
            val recipe = _recipes.value.find { it.id == dish.recipeId } ?: continue
            val mult = (com.easymeals.app.domain.engine.ExactDecimal(dish.servings) /
                    com.easymeals.app.domain.engine.ExactDecimal(recipe.servings)).toString()
            val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(
                recipe = recipe,
                pantryLots = _pantryLots.value,
                multiplier = mult,
                conversions = conversions
            )
            if (!canCook) {
                for ((k, v) in deficits) {
                    val existing = allDeficits[k]
                    if (existing != null) {
                        val sumMissing = com.easymeals.app.domain.engine.ExactDecimal(existing.missingQuantity) +
                                com.easymeals.app.domain.engine.ExactDecimal(v.missingQuantity)
                        allDeficits[k] = existing.copy(missingQuantity = sumMissing.toString())
                    } else {
                        allDeficits[k] = v
                    }
                }
            }
        }
        return Pair(allDeficits.isEmpty(), allDeficits)
    }

    fun eatMeal(planId: String, allowPartial: Boolean = false) {
        val currentPlans = _mealPlans.value.map { it.copy(dishes = it.dishes.toMutableList()) }
        val plan = currentPlans.find { it.id == planId } ?: return
        if (plan.eatenAt != null) return

        if (!allowPartial) {
            val (canEat, deficits) = checkMealStock(planId)
            if (!canEat) {
                throw com.easymeals.app.domain.engine.InsufficientStockException(
                    "Không đủ nguyên liệu để nấu bữa ăn này",
                    deficits
                )
            }
        }

        var updatedPantry = _pantryLots.value
        val allMovs = _stockMovements.value.toMutableList()

        for (dish in plan.dishes) {
            if (dish.isLeftover) continue
            val recipe = _recipes.value.find { it.id == dish.recipeId } ?: continue
            val mult = (com.easymeals.app.domain.engine.ExactDecimal(dish.servings) /
                    com.easymeals.app.domain.engine.ExactDecimal(recipe.servings)).toString()
            val outcome = EasyMealsEngine.executeStockDeduction(
                pantryLots = updatedPantry,
                recipe = recipe,
                mealPlanId = planId,
                idempotencyKey = "android_eat_${planId}_${dish.recipeId}",
                multiplier = mult,
                conversions = conversions,
                allowPartial = allowPartial
            )
            val lotMap = updatedPantry.associateBy { it.id }.toMutableMap()
            for (u in outcome.updatedLots) {
                lotMap[u.id] = u
            }
            updatedPantry = lotMap.values.toList()
            allMovs.addAll(outcome.movements)
        }

        plan.eatenAt = java.time.Instant.now().toString()
        _mealPlans.value = currentPlans
        _pantryLots.value = updatedPantry
        _stockMovements.value = allMovs
        lastActionPlanId = planId
        _undoMessage.value = "Đã ghi nhận bữa ăn và trừ kho!"
        persistState()
    }

    fun addDeficitsToShoppingList(deficits: Collection<DeficitItem>) {
        val current = _shoppingItems.value.toMutableList()
        for (d in deficits) {
            val matching = _ingredients.value.find { it.name.equals(d.ingredientName, ignoreCase = true) }
            val ingId = matching?.id ?: UUID.randomUUID().toString()
            current.add(
                ShoppingItem(
                    ingredientId = ingId,
                    ingredientName = d.ingredientName,
                    neededQuantity = d.missingQuantity,
                    unit = d.unit
                )
            )
        }
        _shoppingItems.value = current
        persistState()
    }

    fun undoLastEatMeal() {
        val planId = lastActionPlanId ?: return
        val currentPlans = _mealPlans.value.map { it.copy(dishes = it.dishes.toMutableList()) }
        val plan = currentPlans.find { it.id == planId } ?: return

        val (restored, revMovs) = EasyMealsEngine.reverseStockMovements(
            pantryLots = _pantryLots.value,
            movements = _stockMovements.value,
            mealPlanId = planId
        )

        val lotMap = _pantryLots.value.associateBy { it.id }.toMutableMap()
        for (r in restored) {
            lotMap[r.id] = r
        }
        val allMovs = _stockMovements.value.toMutableList()
        allMovs.addAll(revMovs)

        plan.eatenAt = null
        _mealPlans.value = currentPlans
        _pantryLots.value = lotMap.values.toList()
        _stockMovements.value = allMovs
        lastActionPlanId = null
        _undoMessage.value = "Đã hoàn tác và khôi phục nguyên liệu!"
        persistState()
    }

    fun clearUndoMessage() {
        _undoMessage.value = null
    }

    fun toggleShoppingItem(id: String) {
        val current = _shoppingItems.value.map {
            if (it.id == id) it.copy(isBought = !it.isBought) else it
        }
        _shoppingItems.value = current
        persistState()
    }

    fun addCustomShoppingItem(name: String, quantity: String, unit: String) {
        val matching = _ingredients.value.find { it.name.equals(name, ignoreCase = true) }
        val ingId = matching?.id ?: UUID.randomUUID().toString()
        val item = ShoppingItem(
            ingredientId = ingId,
            ingredientName = name,
            neededQuantity = quantity,
            unit = unit
        )
        val current = _shoppingItems.value.toMutableList()
        current.add(item)
        _shoppingItems.value = current
        persistState()
    }

    fun bulkAddBoughtToPantry() {
        val bought = _shoppingItems.value.filter { it.isBought }
        for (item in bought) {
            addPantryLot(
                ingredientId = item.ingredientId,
                ingredientName = item.ingredientName,
                quantity = item.neededQuantity,
                unit = item.unit
            )
        }
        _shoppingItems.value = _shoppingItems.value.filter { !it.isBought }
        persistState()
    }

    fun generateNewPlan(days: Int = 3) {
        val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")
        val start = LocalDate.now()
        val end = start.plusDays((days - 1).toLong())

        val (_, meals, shopping) = EasyMealsEngine.generatePeriodPlan(
            startDateStr = start.format(formatter),
            endDateStr = end.format(formatter),
            recipes = _recipes.value,
            currentPantryLots = _pantryLots.value,
            allowLeftovers = _allowLeftovers.value,
            leftoverDays = _leftoverDays.value
        )
        _mealPlans.value = meals
        _shoppingItems.value = shopping
        persistState()
    }

    fun exportBackupJson(): String {
        val payload = BackupPayload(
            appVersion = "2.0.0",
            exportedAt = java.time.Instant.now().toString(),
            pantryLots = _pantryLots.value,
            mealPlans = _mealPlans.value,
            stockMovements = _stockMovements.value,
            shoppingItems = _shoppingItems.value
        )
        return BackupManager.encode(payload)
    }

    fun importBackupPayload(payload: BackupPayload, replace: Boolean = true) {
        if (replace) {
            _pantryLots.value = payload.pantryLots
            _mealPlans.value = payload.mealPlans
            _stockMovements.value = payload.stockMovements
            _shoppingItems.value = payload.shoppingItems
        } else {
            val existingLotIds = _pantryLots.value.map { it.id }.toSet()
            val newLots = _pantryLots.value.toMutableList()
            newLots.addAll(payload.pantryLots.filter { !existingLotIds.contains(it.id) })
            _pantryLots.value = newLots

            val existingShopIds = _shoppingItems.value.map { it.id }.toSet()
            val newShop = _shoppingItems.value.toMutableList()
            newShop.addAll(payload.shoppingItems.filter { !existingShopIds.contains(it.id) })
            _shoppingItems.value = newShop
        }
        persistState()
    }

    fun wipeAllData() {
        _pantryLots.value = emptyList()
        _mealPlans.value = emptyList()
        _stockMovements.value = emptyList()
        _shoppingItems.value = emptyList()
        lastActionPlanId = null
        _undoMessage.value = null
        if (storageFile.exists()) {
            storageFile.delete()
        }
    }

    private data class StateBlob(
        val pantryLots: List<PantryLot>,
        val mealPlans: List<MealPlan>,
        val stockMovements: List<StockMovement>,
        val shoppingItems: List<ShoppingItem>
    )

    private fun persistState() {
        try {
            val blob = StateBlob(
                pantryLots = _pantryLots.value,
                mealPlans = _mealPlans.value,
                stockMovements = _stockMovements.value,
                shoppingItems = _shoppingItems.value
            )
            storageFile.writeText(gson.toJson(blob))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun loadPersistedState() {
        try {
            if (storageFile.exists()) {
                val blob = gson.fromJson(storageFile.readText(), StateBlob::class.java)
                if (blob != null) {
                    _pantryLots.value = blob.pantryLots
                    _mealPlans.value = blob.mealPlans
                    _stockMovements.value = blob.stockMovements
                    _shoppingItems.value = blob.shoppingItems
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
