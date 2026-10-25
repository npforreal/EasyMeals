package com.easymeals.app.util

import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

data class ExpiryStatus(
    val text: String,
    val isWarning: Boolean,
    val isExpired: Boolean,
    val daysRemaining: Long
)

object DateFormatter {
    private val DD_MM_YYYY = DateTimeFormatter.ofPattern("dd/MM/yyyy")
    private val DD_MM = DateTimeFormatter.ofPattern("dd/MM")

    fun formatDateVN(dateStr: String?): String {
        if (dateStr.isNullOrBlank()) return ""
        return try {
            val d = LocalDate.parse(dateStr.take(10))
            d.format(DD_MM_YYYY)
        } catch (_: Exception) {
            dateStr
        }
    }

    fun formatRelativeDate(dateStr: String?, today: LocalDate = LocalDate.now()): String {
        if (dateStr.isNullOrBlank()) return ""
        return try {
            val d = LocalDate.parse(dateStr.take(10))
            val diff = ChronoUnit.DAYS.between(today, d)
            val shortDate = d.format(DD_MM)
            when (diff) {
                0L -> "Hôm nay, $shortDate"
                1L -> "Ngày mai, $shortDate"
                -1L -> "Hôm qua, $shortDate"
                else -> {
                    val dow = when (d.dayOfWeek) {
                        DayOfWeek.MONDAY -> "T2"
                        DayOfWeek.TUESDAY -> "T3"
                        DayOfWeek.WEDNESDAY -> "T4"
                        DayOfWeek.THURSDAY -> "T5"
                        DayOfWeek.FRIDAY -> "T6"
                        DayOfWeek.SATURDAY -> "T7"
                        DayOfWeek.SUNDAY -> "CN"
                        null -> ""
                    }
                    "$dow $shortDate"
                }
            }
        } catch (_: Exception) {
            dateStr
        }
    }

    fun formatExpiryStatus(dateStr: String?, today: LocalDate = LocalDate.now()): ExpiryStatus? {
        if (dateStr.isNullOrBlank()) return null
        return try {
            val d = LocalDate.parse(dateStr.take(10))
            val diff = ChronoUnit.DAYS.between(today, d)
            val formatted = d.format(DD_MM_YYYY)

            when {
                diff < 0 -> ExpiryStatus(
                    text = "Quá hạn ${-diff} ngày ($formatted)",
                    isWarning = true,
                    isExpired = true,
                    daysRemaining = diff
                )
                diff == 0L -> ExpiryStatus(
                    text = "Hết hạn hôm nay ($formatted)",
                    isWarning = true,
                    isExpired = true,
                    daysRemaining = 0
                )
                diff == 1L -> ExpiryStatus(
                    text = "Hết hạn ngày mai ($formatted)",
                    isWarning = true,
                    isExpired = false,
                    daysRemaining = 1
                )
                diff == 2L -> ExpiryStatus(
                    text = "Còn 2 ngày ($formatted)",
                    isWarning = true,
                    isExpired = false,
                    daysRemaining = 2
                )
                else -> ExpiryStatus(
                    text = "Còn $diff ngày ($formatted)",
                    isWarning = false,
                    isExpired = false,
                    daysRemaining = diff
                )
            }
        } catch (_: Exception) {
            null
        }
    }
}
