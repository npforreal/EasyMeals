package com.easymeals.app

import com.easymeals.app.data.ShoppingDefaults
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

/** A4 - Vòng 13: hạn dùng mặc định theo nhóm nguyên liệu. */
class ShoppingDefaultsTest {

    @Test
    fun expiryDaysByCategory() {
        assertEquals(3, ShoppingDefaults.expiryDays("thit"))
        assertEquals(2, ShoppingDefaults.expiryDays("gia_cam"))
        assertEquals(2, ShoppingDefaults.expiryDays("hai_san"))
        assertEquals(7, ShoppingDefaults.expiryDays("trung_sua"))
        assertEquals(5, ShoppingDefaults.expiryDays("rau_cu"))
        assertEquals(10, ShoppingDefaults.expiryDays("cu_qua"))
        assertEquals(180, ShoppingDefaults.expiryDays("gao_bot_mi"))
        assertEquals(180, ShoppingDefaults.expiryDays("gia_vi"))
        assertEquals(180, ShoppingDefaults.expiryDays("nuoc_cham_dau"))
        assertEquals(7, ShoppingDefaults.expiryDays("khac"))
        assertEquals(7, ShoppingDefaults.expiryDays("nhom-khong-tim-thay"))
        assertEquals(7, ShoppingDefaults.expiryDays(null))
    }

    @Test
    fun expiryDateIsPurchasedDatePlusDays() {
        val bought = LocalDate.of(2026, 10, 25)
        val thit = LocalDate.parse(ShoppingDefaults.expiryDate("thit", bought))
        assertEquals(LocalDate.of(2026, 10, 28), thit)
        val haiSan = LocalDate.parse(ShoppingDefaults.expiryDate("hai_san", bought))
        assertEquals(LocalDate.of(2026, 10, 27), haiSan)
        val unknown = ShoppingDefaults.expiryDate("nhom-lạ", bought)
        assertTrue(unknown.matches(Regex("\\d{4}-\\d{2}-\\d{2}")))
    }
}
