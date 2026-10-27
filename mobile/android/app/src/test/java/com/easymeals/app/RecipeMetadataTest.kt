package com.easymeals.app

import com.easymeals.app.util.*
import org.junit.Assert.*
import org.junit.Test

class RecipeMetadataTest {
    @Test fun totalTreatsNullPartAsZero() {
        assertEquals(10, totalMinutes(10, null))
        assertEquals(20, totalMinutes(null, 20))
        assertEquals(30, totalMinutes(10, 20))
        assertNull(totalMinutes(null, null))
    }

    @Test fun timeBoundaries() {
        assertTrue(matchesTime(TimeFilter.LE_15, 5, 10))
        assertFalse(matchesTime(TimeFilter.LE_15, 5, 11))
        assertTrue(matchesTime(TimeFilter.LE_30, 10, 20))
        assertFalse(matchesTime(TimeFilter.LE_30, 10, 21))
        assertTrue(matchesTime(TimeFilter.LE_60, null, 60))
        assertFalse(matchesTime(TimeFilter.LE_60, 30, 31))
    }

    @Test fun unknownTimeExcludedOnlyWhenFilterActive() {
        assertTrue(matchesTime(TimeFilter.ALL, null, null))
        assertFalse(matchesTime(TimeFilter.LE_60, null, null))
    }

    @Test fun difficulty() {
        assertTrue(matchesDifficulty(DifficultyFilter.ALL, null))
        assertFalse(matchesDifficulty(DifficultyFilter.EASY, null))
        assertTrue(matchesDifficulty(DifficultyFilter.EASY, "de"))
        assertTrue(matchesDifficulty(DifficultyFilter.MEDIUM, "trung_binh"))
        assertFalse(matchesDifficulty(DifficultyFilter.HARD, "de"))
        assertEquals("Khó", difficultyLabel("kho"))
        assertNull(difficultyLabel("x"))
    }

    @Test fun host() {
        assertEquals("fda.gov", sourceHost("https://www.fda.gov/food/buy-store-serve-safe-food/safe-food-handling"))
        assertEquals("example.com", sourceHost("http://Example.com:8080/a?b=1"))
        assertNull(sourceHost(null))
        assertNull(sourceHost("  "))
        assertNull(sourceHost("not a url"))
        assertEquals("Nguồn: FDA (phạm vi công cộng)", storageSourceNote("https://www.fda.gov/x"))
        assertNull(storageSourceNote(null))
    }

    @Test fun missingNote() {
        val r = com.easymeals.app.domain.model.Recipe(id = "r", name = "n", category = "c")
        assertEquals("Chưa có dữ liệu thời gian, độ khó, mẹo bảo quản.", missingFieldsNote(r))
        val r2 = r.copy(prepTimeMinutes = 5, difficulty = "de")
        assertEquals("Chưa có dữ liệu mẹo bảo quản.", missingFieldsNote(r2))
        assertEquals("Chuẩn bị ~5 phút · Độ khó: Dễ", metadataSummary(r2))
        assertNull(missingFieldsNote(r2.copy(storageTips = listOf("x"))))
    }
}
