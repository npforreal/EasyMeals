package com.easymeals.app

import com.easymeals.app.domain.history.HistoryAggregator
import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.PantryLot
import com.easymeals.app.domain.model.PlannedDish
import com.easymeals.app.domain.model.Recipe
import com.easymeals.app.domain.model.StockMovement
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

/** F1 - Vòng 13: tổng hợp lịch sử & thống kê tại máy. */
class HistorySummaryTest {

    private val now = LocalDate.parse("2026-10-27")

    private fun lot(
        id: String,
        ingredientId: String = "ing-1",
        remaining: String = "100",
        expiry: String? = null,
        price: String? = null,
        purchasedAt: String? = "2026-10-25"
    ) = PantryLot(
        id = id,
        ingredientId = ingredientId,
        ingredientName = "Nguyên liệu $id",
        remainingQuantity = remaining,
        purchasedQuantity = "500",
        unit = "g",
        purchasedAt = purchasedAt,
        expiresAt = expiry,
        price = price
    )

    private fun plan(
        id: String,
        eatenAt: String?,
        recipeIds: List<Pair<String, Boolean>> = listOf("r-1" to false),
        plannedFor: String = "2026-10-26"
    ) = MealPlan(
        id = id,
        plannedFor = plannedFor,
        mealPeriod = "dinner",
        eatenAt = eatenAt,
        dishes = recipeIds.mapIndexed { index, (recipeId, leftover) ->
            PlannedDish(
                id = "$id-d$index",
                recipeId = recipeId,
                recipeName = "Món $recipeId",
                category = "man",
                isLeftover = leftover,
                servings = 2
            )
        }.toMutableList()
    )

    private fun movement(
        id: String,
        delta: String,
        createdAt: String,
        planId: String? = null,
        ingredientId: String? = null,
        recipeId: String? = null
    ) = StockMovement(
        id = id,
        pantryLotId = "lot-1",
        quantityDelta = delta,
        reason = "meal_consumption",
        mealPlanId = planId,
        createdAt = createdAt,
        ingredientId = ingredientId,
        recipeId = recipeId
    )

    @Test
    fun backfillFillsForeignKeysWithoutOverwriting() {
        val lots = listOf(lot("lot-1", ingredientId = "ing-9"))
        val plans = listOf(
            plan("plan-single", eatenAt = "2026-10-26T12:00:00Z"),
            plan("plan-multi", eatenAt = null, recipeIds = listOf("r-1" to false, "r-2" to false))
        )
        val movements = listOf(
            movement("m1", "-100", "2026-10-26T12:00:00Z", planId = "plan-single"),
            movement("m2", "-100", "2026-10-26T12:00:00Z", planId = "plan-multi"),
            movement("m3", "-100", "2026-10-26T12:00:00Z", planId = "plan-single", ingredientId = "ing-keep", recipeId = "r-keep")
        )

        val (migrated, changed) = HistoryAggregator.backfillMovementIds(movements, lots, plans)

        assertTrue(changed)
        assertEquals("ing-9", migrated[0].ingredientId)
        assertEquals("r-1", migrated[0].recipeId)
        assertEquals("ing-9", migrated[1].ingredientId)
        assertNull("nhiều món thì không suy đoán recipe_id", migrated[1].recipeId)
        assertEquals("ing-keep", migrated[2].ingredientId)
        assertEquals("r-keep", migrated[2].recipeId)
        assertNull(movements[0].ingredientId)
    }

    @Test
    fun countsMealsInsideAndOutsideWindow() {
        val plans = listOf(
            plan("p-recent", eatenAt = "2026-10-26T12:00:00Z", recipeIds = listOf("r-1" to false, "r-1" to true)),
            plan("p-old", eatenAt = "2026-08-01T12:00:00Z", plannedFor = "2026-08-01"),
            plan("p-open", eatenAt = null)
        )
        val summary = HistoryAggregator.build(plans = plans, movements = emptyList(), pantryLots = emptyList(), now = now)

        assertEquals(2, summary.cooked.total)
        assertEquals(1, summary.cooked.inWindow)
        assertEquals(1, summary.leftovers.reusedDishesInWindow)
        assertEquals("p-recent", summary.cooked.meals.first().planId)
        assertEquals(listOf("r-1"), summary.cooked.topRecipes.map { it.recipeId })
        assertEquals(1, summary.cooked.topRecipes[0].count)
    }

    @Test
    fun stockCountsDoNotMixUnits() {
        val movements = listOf(
            movement("m1", "-200", "2026-10-26T12:00:00Z"),
            movement("m2", "-0.5", "2026-10-25T12:00:00Z"),
            movement("m3", "200", "2026-06-01T12:00:00Z")
        )
        val summary = HistoryAggregator.build(plans = emptyList(), movements = movements, pantryLots = emptyList(), now = now)

        assertEquals(3, summary.stock.totalMovements)
        assertEquals(2, summary.stock.inWindow)
        assertEquals(2, summary.stock.consumedCount)
        assertEquals(3, summary.stock.byReason["meal_consumption"])
    }

    @Test
    fun spendingUsesOnlyLotsWithPriceAndReportsMissing() {
        val lots = listOf(
            lot("l1", price = "45000", purchasedAt = "2026-10-25"),
            lot("l2", price = "15000", purchasedAt = "2026-06-01"),
            lot("l3", price = null, purchasedAt = "2026-10-26")
        )
        val summary = HistoryAggregator.build(plans = emptyList(), movements = emptyList(), pantryLots = lots, now = now)

        assertEquals(2, summary.spending.lotsWithPrice)
        assertEquals(1, summary.spending.lotsMissingPrice)
        assertEquals(60000L, summary.spending.total)
        assertEquals(45000L, summary.spending.inWindow)
    }

    @Test
    fun expiredLotsAreListedButWasteIsNotInferred() {
        val lots = listOf(
            lot("l1", remaining = "1", expiry = "2026-10-20"),
            lot("l2", remaining = "1", expiry = null),
            lot("l3", remaining = "0", expiry = "2026-10-01")
        )
        val summary = HistoryAggregator.build(plans = emptyList(), movements = emptyList(), pantryLots = lots, now = now)

        assertFalse(summary.waste.tracked)
        assertEquals(1, summary.waste.expiredLotCount)
        assertEquals("l1", summary.waste.expiredLots[0].lotId)
    }

    @Test
    fun emptyStateDoesNotCrash() {
        val summary = HistoryAggregator.build(plans = emptyList(), movements = emptyList(), pantryLots = emptyList(), now = now)
        assertEquals(0, summary.cooked.total)
        assertEquals(0, summary.stock.totalMovements)
        assertEquals(0L, summary.spending.total)
        assertEquals("2026-09-28", summary.from)
        assertEquals("2026-10-27", summary.to)
    }

    @Test
    fun recipesCatalogueProvidesDisplayNames() {
        val plans = listOf(plan("p1", eatenAt = "2026-10-26T12:00:00Z"))
        val recipes = listOf(
            Recipe(id = "r-1", name = "Thịt kho tàu", category = "man")
        )
        val summary = HistoryAggregator.build(plans = plans, movements = emptyList(), pantryLots = emptyList(), recipes = recipes, now = now)
        assertEquals("Thịt kho tàu", summary.cooked.topRecipes[0].name)
    }
}
