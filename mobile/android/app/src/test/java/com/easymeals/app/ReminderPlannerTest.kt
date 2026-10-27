package com.easymeals.app

import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.PantryLot
import com.easymeals.app.domain.model.PlannedDish
import com.easymeals.app.domain.reminders.ReminderPlanner
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.ZonedDateTime

/** F2 - Vòng 13: nội dung nhắc việc và mốc 09:00 theo múi giờ thiết bị. */
class ReminderPlannerTest {

    private val today = LocalDate.parse("2026-10-27")

    private fun lot(
        id: String,
        name: String = "Sữa",
        remaining: String = "1",
        unit: String = "l",
        expiry: String?
    ) = PantryLot(
        id = id,
        ingredientId = "ing-$id",
        ingredientName = name,
        remainingQuantity = remaining,
        purchasedQuantity = "1",
        unit = unit,
        purchasedAt = "2026-10-25",
        expiresAt = expiry
    )

    private fun plan(
        id: String,
        plannedFor: String = "2026-10-27",
        period: String = "lunch",
        eatenAt: String? = null,
        dishNames: List<String> = listOf("Thịt kho")
    ) = MealPlan(
        id = id,
        plannedFor = plannedFor,
        mealPeriod = period,
        eatenAt = eatenAt,
        dishes = dishNames.mapIndexed { index, name ->
            PlannedDish(
                id = "$id-$index",
                recipeId = "r-$index",
                recipeName = name,
                category = "man",
                isLeftover = false,
                servings = 2
            )
        }.toMutableList()
    )

    @Test
    fun nextTriggerIsTodayAtNineWhenBeforeNine() {
        val now = ZonedDateTime.parse("2026-10-27T07:30:00+07:00[Asia/Ho_Chi_Minh]")
        val next = ReminderPlanner.nextTrigger(now)
        assertEquals(ZonedDateTime.parse("2026-10-27T09:00:00+07:00[Asia/Ho_Chi_Minh]"), next)
    }

    @Test
    fun nextTriggerMovesToTomorrowWhenNineAlreadyPassed() {
        val now = ZonedDateTime.parse("2026-10-27T09:00:00+07:00[Asia/Ho_Chi_Minh]")
        val next = ReminderPlanner.nextTrigger(now)
        assertEquals(ZonedDateTime.parse("2026-10-28T09:00:00+07:00[Asia/Ho_Chi_Minh]"), next)
    }

    @Test
    fun nextTriggerKeepsLocalNineAcrossTimeZones() {
        val now = ZonedDateTime.parse("2026-10-27T12:00:00Z[UTC]")
        val next = ReminderPlanner.nextTrigger(now)
        assertEquals(9, next.hour)
        assertEquals("UTC", next.zone.id)
        assertTrue(next.isAfter(now))
    }

    @Test
    fun digestListsExpiringLotsAndTodaysMeals() {
        val lots = listOf(
            lot("l1", name = "Sữa", expiry = "2026-10-27"),
            lot("l2", name = "Rau muống", expiry = "2026-10-26"),
            lot("l3", name = "Gạo", unit = "kg", expiry = "2026-12-01")
        )
        val plans = listOf(
            plan("p1", period = "dinner", dishNames = listOf("Canh chua")),
            plan("p2", period = "lunch", dishNames = listOf("Thịt kho", "Rau luộc")),
            plan("p3", plannedFor = "2026-10-28")
        )

        val digest = ReminderPlanner.buildDigest(lots, plans, today)!!

        assertTrue(digest.body.contains("Sữa"))
        assertTrue(digest.body.contains("Đã quá hạn"))
        assertTrue(digest.body.contains("Rau muống"))
        assertTrue("lô còn xa hạn không được nhắc", !digest.body.contains("Gạo"))
        assertTrue(digest.body.contains("Trưa: Thịt kho, Rau luộc"))
        assertTrue(digest.body.contains("Tối: Canh chua"))
        assertTrue("không nhắc bữa của ngày khác", !digest.body.contains("2026-10-28"))
    }

    @Test
    fun digestSkipsEatenMealsAndEmptyLots() {
        val lots = listOf(lot("l1", remaining = "0", expiry = "2026-10-26"))
        val plans = listOf(plan("p1", eatenAt = "2026-10-27T12:00:00Z"))
        assertNull(ReminderPlanner.buildDigest(lots, plans, today))
    }

    @Test
    fun digestIsNullWhenNothingToRemind() {
        assertNull(ReminderPlanner.buildDigest(emptyList(), emptyList(), today))
    }

    @Test
    fun formatDayUsesVietnameseOrder() {
        assertEquals("27/10/2026", ReminderPlanner.formatDay(today))
    }
}
