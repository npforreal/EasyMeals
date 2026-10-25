package com.easymeals.app.data

import java.time.LocalDate

/**
 * A4 - Vòng 13: hạn dùng mặc định theo nhóm nguyên liệu (ngày tính từ ngày mua).
 * Dùng chung AppRepository (danh sách đi chợ) và dễ test; nhóm lạ/không rõ về 7 ngày.
 */
object ShoppingDefaults {
    val DEFAULT_EXPIRY_DAYS = mapOf(
        "thit" to 3,
        "gia_cam" to 2,
        "hai_san" to 2,
        "trung_sua" to 7,
        "rau_cu" to 5,
        "cu_qua" to 10,
        "gao_bot_mi" to 180,
        "gia_vi" to 180,
        "nuoc_cham_dau" to 180
    )

    fun expiryDays(category: String?): Int = category?.let { DEFAULT_EXPIRY_DAYS[it] } ?: 7

    fun expiryDate(category: String?, purchasedAt: LocalDate = LocalDate.now()): String {
        return purchasedAt.plusDays(expiryDays(category).toLong()).toString()
    }
}
