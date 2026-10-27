package com.easymeals.app.domain.history

import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.PantryLot
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.domain.model.StockMovement
import java.time.LocalDate
import java.time.temporal.ChronoUnit

/**
 * F1 - Vòng 13: lịch sử & thống kê tính hoàn toàn trên thiết bị.
 *
 * Quy ước schema (quyết định 2026-10-27): biến động kho chỉ thêm khoá ngoại tuỳ chọn
 * `ingredient_id`, `recipe_id`, `leftover_source_meal_id`; không lưu bản sao tên.
 * Không có API nào nhận dữ liệu lịch sử.
 */
data class HistoryMeal(
    val planId: String,
    val plannedFor: String,
    val mealPeriod: String,
    val eatenAt: String,
    val dishNames: List<String>,
    val recipeIds: List<String>,
    val servingsTotal: Int,
    val leftoverReuseCount: Int
)

data class HistoryTopRecipe(val recipeId: String, val name: String, val count: Int)

data class HistoryCooked(
    val total: Int,
    val inWindow: Int,
    val lastEatenAt: String?,
    val meals: List<HistoryMeal>,
    val topRecipes: List<HistoryTopRecipe>
)

data class HistoryStock(
    val totalMovements: Int,
    val inWindow: Int,
    val consumedCount: Int,
    val restoredCount: Int,
    val byReason: Map<String, Int>
)

data class HistoryLeftovers(val reusedDishesInWindow: Int, val available: Boolean)

data class HistoryExpiredLot(
    val lotId: String,
    val ingredientId: String,
    val ingredientName: String,
    val remainingQuantity: String,
    val unit: String,
    val expiresAt: String
)

data class HistoryWaste(
    val tracked: Boolean,
    val expiredLotCount: Int,
    val expiredLots: List<HistoryExpiredLot>
)

data class HistorySpending(
    val currency: String,
    val total: Long,
    val inWindow: Long,
    val lotsWithPrice: Int,
    val lotsMissingPrice: Int
)

data class HistorySummary(
    val windowDays: Int,
    val from: String,
    val to: String,
    val cooked: HistoryCooked,
    val stock: HistoryStock,
    val leftovers: HistoryLeftovers,
    val waste: HistoryWaste,
    val spending: HistorySpending
)

object HistoryAggregator {

    private val DAY_PREFIX = Regex("^\\d{4}-\\d{2}-\\d{2}")

    private fun dayOf(value: String?): String? {
        if (value == null || value.length < 10) return null
        val prefix = value.substring(0, 10)
        if (!DAY_PREFIX.matches(prefix)) return null
        return runCatching { LocalDate.parse(prefix).toString() }.getOrNull()
    }

    private fun number(value: String?): Double = value?.toDoubleOrNull() ?: 0.0

    /**
     * Điền khoá ngoại cho movements cũ. Trả về danh sách mới + cờ thay đổi.
     * Không ghi đè giá trị đã có, không xoá bản ghi nào.
     */
    fun backfillMovementIds(
        movements: List<StockMovement>,
        lots: List<PantryLot>,
        plans: List<MealPlan>
    ): Pair<List<StockMovement>, Boolean> {
        val lotById = lots.associateBy { it.id }
        val planById = plans.associateBy { it.id }
        var changed = false

        val result = movements.map { movement ->
            var next = movement
            if (next.ingredientId.isNullOrEmpty()) {
                val ingredientId = lotById[next.pantryLotId]?.ingredientId
                if (!ingredientId.isNullOrEmpty()) {
                    next = next.copy(ingredientId = ingredientId)
                    changed = true
                }
            }
            if (next.recipeId.isNullOrEmpty() && next.mealPlanId != null) {
                val cooked = planById[next.mealPlanId]
                    ?.dishes
                    ?.filter { !it.isLeftover }
                    .orEmpty()
                if (cooked.size == 1 && cooked[0].recipeId.isNotEmpty()) {
                    next = next.copy(recipeId = cooked[0].recipeId)
                    changed = true
                }
            }
            next
        }
        return result to changed
    }

    fun build(
        plans: List<MealPlan>,
        movements: List<StockMovement>,
        pantryLots: List<PantryLot>,
        recipes: List<Recipe> = emptyList(),
        now: LocalDate = LocalDate.now(),
        windowDays: Int = 30
    ): HistorySummary {
        val window = if (windowDays > 0) windowDays else 30
        val to = now.toString()
        val from = now.minus((window - 1).toLong(), ChronoUnit.DAYS).toString()

        fun inWindow(value: String?): Boolean {
            val day = dayOf(value) ?: return false
            return day >= from && day <= to
        }

        val recipeNames = mutableMapOf<String, String>()
        recipes.forEach { recipeNames[it.id] = it.name.ifEmpty { it.id } }
        plans.forEach { plan ->
            plan.dishes.forEach { dish ->
                if (!recipeNames.containsKey(dish.recipeId) && dish.recipeName.isNotEmpty()) {
                    recipeNames[dish.recipeId] = dish.recipeName
                }
            }
        }

        // ---- Bữa đã nấu ----
        val eatenPlans = plans
            .filter { !it.eatenAt.isNullOrEmpty() }
            .sortedByDescending { it.eatenAt }

        val meals = eatenPlans.map { plan ->
            val cooked = plan.dishes.filter { !it.isLeftover }
            val leftovers = plan.dishes.count { it.isLeftover }
            HistoryMeal(
                planId = plan.id,
                plannedFor = dayOf(plan.plannedFor) ?: plan.plannedFor,
                mealPeriod = plan.mealPeriod,
                eatenAt = plan.eatenAt ?: "",
                dishNames = cooked.map { it.recipeName.ifEmpty { recipeNames[it.recipeId] ?: it.recipeId } },
                recipeIds = cooked.map { it.recipeId }.filter { it.isNotEmpty() },
                servingsTotal = cooked.sumOf { it.servings },
                leftoverReuseCount = leftovers
            )
        }

        val mealsInWindow = meals.filter { inWindow(it.eatenAt) }

        val counts = mutableMapOf<String, Int>()
        mealsInWindow.forEach { meal -> meal.recipeIds.forEach { counts[it] = (counts[it] ?: 0) + 1 } }
        val topRecipes = counts.entries
            .map { HistoryTopRecipe(it.key, recipeNames[it.key] ?: it.key, it.value) }
            .sortedWith(compareByDescending<HistoryTopRecipe> { it.count }.thenBy { it.name })
            .take(5)

        // ---- Biến động kho (đếm, không cộng trộn đơn vị) ----
        val byReason = mutableMapOf<String, Int>()
        var movementsInWindow = 0
        var consumed = 0
        var restored = 0
        movements.forEach { movement ->
            val reason = movement.reason.ifEmpty { "unknown" }
            byReason[reason] = (byReason[reason] ?: 0) + 1
            if (!inWindow(movement.createdAt)) return@forEach
            movementsInWindow += 1
            val delta = number(movement.quantityDelta)
            if (delta < 0) consumed += 1
            if (delta > 0) restored += 1
        }

        // ---- Đồ dư & đồ quá hạn ----
        val leftoverReuse = mealsInWindow.sumOf { it.leftoverReuseCount }
        val expired = pantryLots
            .mapNotNull { lot ->
                val expiry = dayOf(lot.expiresAt) ?: return@mapNotNull null
                if (expiry >= to || number(lot.remainingQuantity) <= 0) return@mapNotNull null
                HistoryExpiredLot(
                    lotId = lot.id,
                    ingredientId = lot.ingredientId,
                    ingredientName = lot.ingredientName,
                    remainingQuantity = lot.remainingQuantity,
                    unit = lot.unit,
                    expiresAt = expiry
                )
            }
            .sortedBy { it.expiresAt }

        // ---- Chi tiêu đã nhập ----
        var total = 0L
        var inWindowTotal = 0L
        var withPrice = 0
        var missingPrice = 0
        pantryLots.forEach { lot ->
            val price = lot.price?.toLongOrNull()
            if (price != null && price >= 0) {
                withPrice += 1
                total += price
                if (inWindow(lot.purchasedAt)) inWindowTotal += price
            } else {
                missingPrice += 1
            }
        }

        return HistorySummary(
            windowDays = window,
            from = from,
            to = to,
            cooked = HistoryCooked(
                total = meals.size,
                inWindow = mealsInWindow.size,
                lastEatenAt = meals.firstOrNull()?.eatenAt,
                meals = meals,
                topRecipes = topRecipes
            ),
            stock = HistoryStock(
                totalMovements = movements.size,
                inWindow = movementsInWindow,
                consumedCount = consumed,
                restoredCount = restored,
                byReason = byReason
            ),
            leftovers = HistoryLeftovers(
                reusedDishesInWindow = leftoverReuse,
                available = mealsInWindow.isNotEmpty()
            ),
            waste = HistoryWaste(
                tracked = false,
                expiredLotCount = expired.size,
                expiredLots = expired
            ),
            spending = HistorySpending(
                currency = "VND",
                total = total,
                inWindow = inWindowTotal,
                lotsWithPrice = withPrice,
                lotsMissingPrice = missingPrice
            )
        )
    }
}
