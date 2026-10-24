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
}
