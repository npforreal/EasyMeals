package com.easymeals.app.data.backup

import com.easymeals.app.domain.model.*
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.google.gson.annotations.SerializedName
import java.io.InputStream
import java.io.InputStreamReader
import java.time.Instant

data class BackupPayload(
    @SerializedName("schema_version") val schemaVersion: Int? = null,
    @SerializedName("app_version") val appVersion: String = "2.0.0",
    @SerializedName("exported_at") val exportedAt: String = Instant.now().toString(),
    @SerializedName("pantry_lots") val pantryLots: List<PantryLot> = emptyList(),
    @SerializedName("meal_plans") val mealPlans: List<MealPlan> = emptyList(),
    @SerializedName("stock_movements") val stockMovements: List<StockMovement> = emptyList(),
    @SerializedName("shopping_items") val shoppingItems: List<ShoppingItem> = emptyList(),
    @SerializedName("recipe_preferences") val recipePreferences: RecipePreferences? = null
)

data class RecipePreferences(
    @SerializedName("avoided_ingredient_ids") val avoidedIngredientIds: Set<String> = emptySet(),
    @SerializedName("preferred_ingredient_ids") val preferredIngredientIds: Set<String> = emptySet(),
    @SerializedName("dietary_filter") val dietaryFilter: String = "",
    @SerializedName("max_spice") val maxSpice: String = ""
)

object BackupManager {
    /** Phiên bản định dạng sao lưu hiện tại (F1 thêm khoá ngoại movements, F3 thêm thông tin phiên bản). */
    const val SCHEMA_VERSION = 3
    const val APP_VERSION = "2.0.0"

    private val gson: Gson = GsonBuilder().setPrettyPrinting().create()

    fun validateAndDecode(stream: InputStream): BackupPayload {
        val reader = InputStreamReader(stream, Charsets.UTF_8)
        return decode(reader.readText())
    }

    /**
     * F3: đọc được cả hai định dạng để chuyển thiết bị:
     * - Định dạng phẳng của ứng dụng di động (`pantry_lots`, `meal_plans`, ...).
     * - Định dạng của bản Web (`data.pantry`, `data.plans`, ...).
     */
    fun decode(jsonString: String): BackupPayload {
        if (jsonString.isBlank()) {
            throw IllegalArgumentException("File sao lưu rỗng hoặc sai cấu trúc JSON.")
        }
        val root = try {
            JsonParser.parseString(jsonString).asJsonObject
        } catch (e: Exception) {
            throw IllegalArgumentException(
                "Không đọc được JSON: ${e.message ?: "cú pháp không hợp lệ"}. " +
                    "Hãy kiểm tra tệp có bị cắt ngắn hoặc không phải JSON không."
            )
        }
        val hasWebData = root.has("data") && root.get("data").isJsonObject
        val source = if (hasWebData) webToMobile(root) else root

        val payload = try {
            gson.fromJson(source, BackupPayload::class.java)
        } catch (e: Exception) {
            throw IllegalArgumentException(
                "Cấu trúc dữ liệu không khớp: ${e.message ?: "trường bắt buộc bị thiếu"}. " +
                    "Hãy thử xuất lại bản sao lưu từ ứng dụng."
            )
        } ?: throw IllegalArgumentException("Chuỗi JSON sao lưu rỗng hoặc sai cấu trúc.")

        val version = payload.schemaVersion ?: 1
        if (version > SCHEMA_VERSION) {
            throw IllegalArgumentException(
                "Bản sao lưu dùng schema $version, ứng dụng chỉ hỗ trợ đến $SCHEMA_VERSION. " +
                    "Hãy cập nhật EasyMeals lên bản mới rồi thử lại."
            )
        }
        return payload
    }

    /** Chuyển định dạng Web (`data.*`) sang định dạng phẳng của ứng dụng di động. */
    private fun webToMobile(root: JsonObject): JsonObject {
        val data = root.getAsJsonObject("data")
        val mapped = JsonObject()
        root.get("schema_version")?.let { mapped.add("schema_version", it) }
        root.get("app_version")?.let { mapped.add("app_version", it) }
        root.get("exported_at")?.let { mapped.add("exported_at", it) }
        data.get("pantry")?.let { mapped.add("pantry_lots", it) }
        data.get("plans")?.let { mapped.add("meal_plans", it) }
        data.get("movements")?.let { mapped.add("stock_movements", it) }
        data.get("shopping")?.let { mapped.add("shopping_items", it) }
        // Tuỳ chọn công thức của Web nằm trong store settings (khoá recipe_preferences_v1).
        val settings = data.get("settings")
        if (settings != null && settings.isJsonArray) {
            val prefs = settings.asJsonArray
                .mapNotNull { runCatching { it.asJsonObject }.getOrNull() }
                .firstOrNull { it.get("key")?.asString == "recipe_preferences_v1" }
                ?.get("value")?.takeIf { it.isJsonObject }?.asJsonObject
            if (prefs != null) {
                val out = JsonObject()
                prefs.get("avoidedIngredientIds")?.let { out.add("avoided_ingredient_ids", it) }
                prefs.get("preferredIngredientIds")?.let { out.add("preferred_ingredient_ids", it) }
                prefs.get("dietaryFilter")?.let { out.add("dietary_filter", it) }
                prefs.get("maxSpice")?.let { out.add("max_spice", it) }
                mapped.add("recipe_preferences", out)
            }
        }
        return mapped
    }

    fun encode(payload: BackupPayload): String {
        return gson.toJson(payload)
    }

    /**
     * A3 - Vòng 13: migration tương thích với backup cũ.
     * Gson bỏ qua giá trị mặc định Kotlin khi thiếu khoá, nên bản sao lưu cũ
     * không có `shopping_items` sẽ cho null → phải vá về danh sách rỗng trước khi import.
     */
    fun sanitize(payload: BackupPayload): BackupPayload = BackupPayload(
        schemaVersion = payload.schemaVersion ?: 1,
        appVersion = payload.appVersion,
        exportedAt = payload.exportedAt,
        pantryLots = payload.pantryLots ?: emptyList(),
        mealPlans = payload.mealPlans ?: emptyList(),
        stockMovements = payload.stockMovements ?: emptyList(),
        shoppingItems = payload.shoppingItems ?: emptyList(),
        recipePreferences = payload.recipePreferences ?: RecipePreferences()
    )
}
