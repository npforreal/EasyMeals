package com.easymeals.app

import com.easymeals.app.data.backup.BackupManager
import com.easymeals.app.domain.model.ShoppingItem
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * A3 (Vòng 13): backup cũ (thiếu shopping_items / is_manually_added) vẫn nhập được.
 * Gson không áp dụng giá trị mặc định Kotlin khi thiếu khoá -> phải qua sanitize.
 */
class BackupMigrationTest {

    @Test
    fun legacyBackupWithoutShoppingItemsIsSanitized() {
        val legacyJson = """
            {
              "app_version": "2.0.0",
              "exported_at": "2026-10-25T00:00:00Z",
              "pantry_lots": [
                {
                  "id": "lot-1",
                  "ingredient_id": "ing-1",
                  "ingredient_name": "Thịt ba chỉ",
                  "purchased_quantity": "1000",
                  "remaining_quantity": "800",
                  "unit": "g",
                  "purchased_at": "2026-10-25"
                }
              ],
              "meal_plans": [],
              "stock_movements": []
            }
        """.trimIndent()

        val payload = BackupManager.decode(legacyJson)
        // Bản cũ thiếu khoá shopping_items -> danh sách rỗng (không đổ lỗi/văng khi import).
        assertEquals(1, payload.pantryLots.size)
        assertEquals(0, payload.shoppingItems.size)

        val sanitized = BackupManager.sanitize(payload)
        assertEquals(1, sanitized.pantryLots.size)
        assertEquals("Thịt ba chỉ", sanitized.pantryLots[0].ingredientName)
        assertEquals(emptyList<Any>(), sanitized.shoppingItems)
        assertEquals(emptyList<Any>(), sanitized.mealPlans)
        assertEquals(emptyList<Any>(), sanitized.stockMovements)
    }

    @Test
    fun legacyBackupWithShoppingItemsButWithoutSourceFlag() {
        val legacyJson = """
            {
              "app_version": "2.0.0",
              "exported_at": "2026-10-25T00:00:00Z",
              "pantry_lots": [],
              "meal_plans": [],
              "stock_movements": [],
              "shopping_items": [
                {
                  "ingredient_id": "ing-9",
                  "ingredient_name": "Nước mắm",
                  "needed_quantity": "500",
                  "unit": "ml",
                  "is_bought": true,
                  "dish_names": ["Món cũ"]
                }
              ]
            }
        """.trimIndent()

        val payload = BackupManager.decode(legacyJson)
        val sanitized = BackupManager.sanitize(payload)
        assertEquals(1, sanitized.shoppingItems.size)
        val item = sanitized.shoppingItems[0]
        assertEquals("ing-9", item.ingredientId)
        assertTrue(item.isBought)
        // Bản cũ không có trường nguồn phát sinh -> coi như mục sinh tự (không phải tự thêm).
        assertFalse(item.isManuallyAdded)
    }

    @Test
    fun shoppingItemLegacyDecodeDefaultsSourceFlag() {
        val gson = Gson()
        val legacy = gson.fromJson("""{"ingredient_id": "i", "ingredient_name": "X", "needed_quantity": "1", "unit": "g"}""", ShoppingItem::class.java)
        assertFalse(legacy.isManuallyAdded)
        val manual = gson.fromJson("""{"ingredient_id": "i", "needed_quantity": "1", "unit": "g", "is_manually_added": true}""", ShoppingItem::class.java)
        assertTrue(manual.isManuallyAdded)
        assertEquals("i_g", manual.id)
    }

    @Test
    fun recipePreferencesBackupSupportsLegacyAndCurrentSchemas() {
        val legacy = BackupManager.sanitize(BackupManager.decode("""{"pantry_lots":[],"meal_plans":[],"stock_movements":[],"shopping_items":[]}"""))
        assertEquals(1, legacy.schemaVersion)
        assertTrue(legacy.recipePreferences!!.avoidedIngredientIds.isEmpty())

        val current = BackupManager.sanitize(BackupManager.decode("""{"schema_version":2,"recipe_preferences":{"avoided_ingredient_ids":["ing-a"],"preferred_ingredient_ids":["ing-b"],"dietary_filter":"vegan","max_spice":"2"}}"""))
        assertEquals(setOf("ing-a"), current.recipePreferences!!.avoidedIngredientIds)
        assertEquals(setOf("ing-b"), current.recipePreferences!!.preferredIngredientIds)
        assertEquals("vegan", current.recipePreferences!!.dietaryFilter)
        assertEquals("2", current.recipePreferences!!.maxSpice)
    }
}
