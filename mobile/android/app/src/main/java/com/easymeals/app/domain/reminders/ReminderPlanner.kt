package com.easymeals.app.domain.reminders

import com.easymeals.app.domain.model.MealPlan
import com.easymeals.app.domain.model.PantryLot
import java.time.LocalDate
import java.time.ZonedDateTime

/**
 * F2 - Vòng 13: nội dung nhắc việc cục bộ (không gọi mạng, không gửi dữ liệu đi).
 *
 * Chỉ dùng dữ liệu đang có trên máy:
 * - Lô sắp hết hạn / đã quá hạn nhưng còn hàng trong tủ.
 * - Bữa ăn hôm nay chưa đánh dấu "Đã ăn" (gợi ý chuẩn bị/rã đông trước).
 *
 * Không có dữ liệu rã đông riêng, nên phần "chuẩn bị" chỉ là lời nhắc chung cho bữa hôm nay,
 * không suy diễn thời gian rã đông.
 */
data class ReminderDigest(
    val title: String,
    val body: String
)

object ReminderPlanner {

    /** Giờ nhắc cố định theo múi giờ của thiết bị. */
    const val REMINDER_HOUR = 9

    /** Số ngày nhắc trước hạn dùng. */
    const val EXPIRY_WINDOW_DAYS = 2

    private const val MAX_EXPIRY_LINES = 3
    private const val MAX_MEAL_LINES = 2

    private fun dayOf(value: String?): LocalDate? {
        if (value == null || value.length < 10) return null
        return runCatching { LocalDate.parse(value.substring(0, 10)) }.getOrNull()
    }

    private fun periodLabel(period: String): String = when (period) {
        "breakfast" -> "Sáng"
        "lunch" -> "Trưa"
        "dinner" -> "Tối"
        else -> period
    }

    /**
     * Tạo nội dung nhắc cho một ngày. Trả về `null` khi không có gì cần nhắc
     * (tránh gửi thông báo rỗng).
     */
    fun buildDigest(
        pantryLots: List<PantryLot>,
        mealPlans: List<MealPlan>,
        date: LocalDate,
        expiryWindowDays: Int = EXPIRY_WINDOW_DAYS
    ): ReminderDigest? {
        val window = if (expiryWindowDays >= 0) expiryWindowDays else EXPIRY_WINDOW_DAYS
        val limit = date.plusDays(window.toLong())
        val lines = mutableListOf<String>()

        val expiring = pantryLots
            .mapNotNull { lot ->
                val expiry = dayOf(lot.expiresAt) ?: return@mapNotNull null
                if (expiry.isAfter(limit)) return@mapNotNull null
                if ((lot.remainingQuantity.toDoubleOrNull() ?: 0.0) <= 0.0) return@mapNotNull null
                Triple(lot, expiry, expiry.isBefore(date))
            }
            .sortedBy { it.second }
            .take(MAX_EXPIRY_LINES)

        for ((lot, expiry, overdue) in expiring) {
            val name = lot.ingredientName.ifBlank { lot.ingredientId }
            val prefix = if (overdue) "Đã quá hạn" else "Sắp hết hạn"
            lines.add("$prefix: $name (${lot.remainingQuantity} ${lot.unit}, hạn ${formatDay(expiry)})")
        }

        val today = date.toString()
        val meals = mealPlans
            .filter { it.eatenAt.isNullOrEmpty() }
            .filter { it.plannedFor.take(10) == today }
            .sortedBy { periodOrder(it.mealPeriod) }
            .take(MAX_MEAL_LINES)

        for (plan in meals) {
            val dishNames = plan.dishes
                .filterNot { it.isLeftover }
                .map { it.recipeName.ifBlank { it.recipeId } }
                .filter { it.isNotBlank() }
            if (dishNames.isEmpty()) continue
            lines.add("Hôm nay · ${periodLabel(plan.mealPeriod)}: ${dishNames.joinToString(", ")}")
        }

        if (lines.isEmpty()) return null
        return ReminderDigest(
            title = "EasyMeals · nhắc việc hôm nay",
            body = lines.joinToString("\n")
        )
    }

    private fun periodOrder(period: String): Int = when (period) {
        "breakfast" -> 0
        "lunch" -> 1
        "dinner" -> 2
        else -> 3
    }

    /**
     * Mốc nhắc kế tiếp lúc 09:00 theo múi giờ của thiết bị.
     * Dùng ZonedDateTime nên tự đúng khi đổi múi giờ hoặc chuyển DST.
     */
    fun nextTrigger(now: ZonedDateTime, hour: Int = REMINDER_HOUR): ZonedDateTime {
        val safeHour = hour.coerceIn(0, 23)
        var candidate = now
            .withHour(safeHour)
            .withMinute(0)
            .withSecond(0)
            .withNano(0)
        if (!candidate.isAfter(now)) {
            candidate = candidate.plusDays(1)
        }
        return candidate
    }

    fun formatDay(date: LocalDate): String {
        val day = date.dayOfMonth.toString().padStart(2, '0')
        val month = date.monthValue.toString().padStart(2, '0')
        return "$day/$month/${date.year}"
    }
}
