package com.easymeals.app

import com.easymeals.app.data.catalogue.CatalogueLoader
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.FileInputStream
import java.io.InputStream

class CatalogueLoadingTest {

    @Test
    fun testLoadRealCatalogueAsset() {
        // Tìm file catalogue.json từ thư mục assets hoặc test resources
        val fileCandidates = listOf(
            File("src/main/assets/catalogue.json"),
            File("mobile/android/app/src/main/assets/catalogue.json"),
            File("../../data/catalogue.json")
        )
        val file = fileCandidates.firstOrNull { it.exists() }
        assertNotNull("Phải tìm thấy file catalogue.json thật", file)

        val stream: InputStream = FileInputStream(file!!)
        val bundle = stream.use { CatalogueLoader.loadCatalogue(it) }

        assertNotNull("CatalogueBundle không được null", bundle)
        assertFalse("Catalogue version không được rỗng", bundle.version.isNullOrBlank())
        assertEquals("Số lượng món ăn phải là 133", 133, bundle.recipes.size)
        assertTrue("Số lượng nguyên liệu phải >= 147", bundle.ingredients.size >= 147)

        for (ing in bundle.ingredients) {
            assertNotNull("ID nguyên liệu không được null", ing.id)
            assertTrue("ID nguyên liệu không được rỗng", ing.id.isNotBlank())
            assertNotNull("Tên nguyên liệu không được null", ing.name)
            assertTrue("Tên nguyên liệu không được rỗng", ing.name.isNotBlank())
            assertNotNull("default_unit của ${ing.name} không được null", ing.defaultUnit)
            assertTrue("default_unit của ${ing.name} không được rỗng", ing.defaultUnit!!.isNotBlank())
            assertNotNull("category của ${ing.name} không được null", ing.category)
        }

        for (recipe in bundle.recipes) {
            assertNotNull("ID món ăn không được null", recipe.id)
            assertNotNull("Tên món ăn không được null", recipe.name)
            assertNotNull("Nhóm món ăn không được null", recipe.category)
            assertTrue("Số lượng người ăn phải > 0", recipe.servings > 0)
            assertTrue("Món ${recipe.name} phải có nguyên liệu", recipe.ingredients.isNotEmpty())
        }
    }
}
