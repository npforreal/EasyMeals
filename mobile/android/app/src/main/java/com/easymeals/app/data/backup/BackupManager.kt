package com.easymeals.app.data.backup

import com.easymeals.app.domain.model.*
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.annotations.SerializedName
import java.io.InputStream
import java.io.InputStreamReader
import java.time.Instant

data class BackupPayload(
    @SerializedName("app_version") val appVersion: String = "2.0.0",
    @SerializedName("exported_at") val exportedAt: String = Instant.now().toString(),
    @SerializedName("pantry_lots") val pantryLots: List<PantryLot> = emptyList(),
    @SerializedName("meal_plans") val mealPlans: List<MealPlan> = emptyList(),
    @SerializedName("stock_movements") val stockMovements: List<StockMovement> = emptyList(),
    @SerializedName("shopping_items") val shoppingItems: List<ShoppingItem> = emptyList()
)

object BackupManager {
    private val gson: Gson = GsonBuilder().setPrettyPrinting().create()

    fun validateAndDecode(stream: InputStream): BackupPayload {
        val reader = InputStreamReader(stream, Charsets.UTF_8)
        return gson.fromJson(reader, BackupPayload::class.java)
            ?: throw IllegalArgumentException("File sao lưu rỗng hoặc sai cấu trúc JSON.")
    }

    fun decode(jsonString: String): BackupPayload {
        return gson.fromJson(jsonString, BackupPayload::class.java)
            ?: throw IllegalArgumentException("Chuỗi JSON sao lưu rỗng hoặc sai cấu trúc.")
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
        appVersion = payload.appVersion,
        exportedAt = payload.exportedAt,
        pantryLots = payload.pantryLots ?: emptyList(),
        mealPlans = payload.mealPlans ?: emptyList(),
        stockMovements = payload.stockMovements ?: emptyList(),
        shoppingItems = payload.shoppingItems ?: emptyList()
    )
}
