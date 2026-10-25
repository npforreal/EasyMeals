package com.easymeals.app.data.db

import android.content.Context
import com.easymeals.app.data.backup.BackupManager
import com.easymeals.app.data.backup.BackupPayload
import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.domain.engine.EasyMealsEngine
import com.easymeals.app.domain.model.*
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

    fun eatMeal(planId: String) {
        val currentPlans = _mealPlans.value.map { it.copy(dishes = it.dishes.toMutableList()) }
        val plan = currentPlans.find { it.id == planId } ?: return
        if (plan.eatenAt != null) return

        var updatedPantry = _pantryLots.value
        val allMovs = _stockMovements.value.toMutableList()

        for (dish in plan.dishes) {
            if (dish.isLeftover) continue
            val recipe = _recipes.value.find { it.id == dish.recipeId } ?: continue
            val (updated, movs) = EasyMealsEngine.deductRecipeStockFifo(
                pantryLots = updatedPantry,
                recipe = recipe,
                mealPlanId = planId,
                idempotencyKey = "android_eat_$planId"
            )
            val lotMap = updatedPantry.associateBy { it.id }.toMutableMap()
            for (u in updated) {
                lotMap[u.id] = u
            }
            updatedPantry = lotMap.values.toList()
            allMovs.addAll(movs)
        }

        plan.eatenAt = java.time.Instant.now().toString()
        _mealPlans.value = currentPlans
        _pantryLots.value = updatedPantry
        _stockMovements.value = allMovs
        lastActionPlanId = planId
        _undoMessage.value = "Đã ghi nhận bữa ăn và trừ kho!"
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
            allowLeftovers = true
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
