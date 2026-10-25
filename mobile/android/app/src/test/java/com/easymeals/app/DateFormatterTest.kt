package com.easymeals.app

import com.easymeals.app.util.DateFormatter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class DateFormatterTest {

    @Test
    fun testFormatDateVN() {
        assertEquals("25/10/2026", DateFormatter.formatDateVN("2026-10-25"))
    }

    @Test
    fun testFormatRelativeDate() {
        val today = LocalDate.of(2026, 10, 25) // Sunday
        assertEquals("Hôm nay, 25/10", DateFormatter.formatRelativeDate("2026-10-25", today))
        assertEquals("Ngày mai, 26/10", DateFormatter.formatRelativeDate("2026-10-26", today))
        assertEquals("Hôm qua, 24/10", DateFormatter.formatRelativeDate("2026-10-24", today))
        // 2026-10-27 is Tuesday -> T3
        assertEquals("T3 27/10", DateFormatter.formatRelativeDate("2026-10-27", today))
    }

    @Test
    fun testFormatExpiryStatus() {
        val today = LocalDate.of(2026, 10, 25)

        val exp0 = DateFormatter.formatExpiryStatus("2026-10-25", today)!!
        assertTrue(exp0.isWarning)
        assertTrue(exp0.isExpired)

        val exp1 = DateFormatter.formatExpiryStatus("2026-10-26", today)!!
        assertTrue(exp1.isWarning)
        assertFalse(exp1.isExpired)

        val exp2 = DateFormatter.formatExpiryStatus("2026-10-27", today)!!
        assertTrue(exp2.isWarning)
        assertFalse(exp2.isExpired)

        val expSafe = DateFormatter.formatExpiryStatus("2026-10-30", today)!!
        assertFalse(expSafe.isWarning)
        assertFalse(expSafe.isExpired)
    }
}
