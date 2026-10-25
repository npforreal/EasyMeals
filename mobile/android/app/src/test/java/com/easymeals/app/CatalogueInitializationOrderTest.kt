package com.easymeals.app

import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.domain.engine.EasyMealsEngine
import com.easymeals.app.domain.model.PantryLot
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.FileInputStream
import java.io.InputStream

/**
 * Test hồi quy lỗi thứ tự khởi tạo: `conversions` bị ghi đè thành rỗng vì khai báo sau khối `init`.
 *
 * Bản sửa: khai báo `var conversions` TRƯỚC khối `init` trong `AppRepository` (đã có trong working tree,
 * chưa commit). Test này nạp catalogue thật từ `data/catalogue.json` và khẳng định:
 *  1. `bundle.conversions` không rỗng.
 *  2. `getTotalIngredientStock` cho 500 g gạo → 1250 g cơm nóng (ratio 2.5).
 */
class CatalogueInitializationOrderTest {

    // ID đã biết trong data/catalogue.json (xem file)
    private val ID_GAO = "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b"
    private val ID_COM_NONG = "412a8c08-4863-5000-aedd-13e2ba3adb69"

    private fun loadRealCatalogue(): com.easymeals.app.domain.model.CatalogueBundle {
        val fileCandidates = listOf(
            File("src/main/assets/catalogue.json"),
            File("mobile/android/app/src/main/assets/catalogue.json"),
            File("../../data/catalogue.json")
        )
        val file = fileCandidates.firstOrNull { it.exists() }
        assertNotNull("Phải tìm thấy file catalogue.json thật", file)
        val stream: InputStream = FileInputStream(file!!)
        return stream.use { CatalogueLoader.loadCatalogue(it) }
    }

    @Test
    fun testConversionsNotEmptyAfterCatalogueLoad() {
        val bundle = loadRealCatalogue()

        // Lỗi trước khi sửa: conversions bị ghi đè thành emptyList() sau init → danh mục rỗng.
        assertTrue("Conversions không được rỗng sau khi nạp catalogue thật", bundle.conversions.isNotEmpty())
    }

    @Test
    fun testGetTotalIngredientStock_GaoToComNong() {
        val bundle = loadRealCatalogue()

        val lot = PantryLot(
            id = "test-lot-gao-1",
            ingredientId = ID_GAO,
            ingredientName = "Gạo",
            remainingQuantity = "500",
            purchasedQuantity = "500",
            unit = "g",
            purchasedAt = "2026-01-01",
            expiresAt = null
        )

        // 500 g gạo × ratio 2.5 = 1250 g cơm nóng
        val total = EasyMealsEngine.getTotalIngredientStock(
            pantryLots = listOf(lot),
            ingredientId = ID_COM_NONG,
            targetUnit = "g",
            conversions = bundle.conversions
        )
        assertEquals("500g gạo phải quy đổi thành 1250g cơm nóng (ratio 2.5)", "1250", total.toString())
    }
}
