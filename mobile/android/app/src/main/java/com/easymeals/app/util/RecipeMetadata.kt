package com.easymeals.app.util

import com.easymeals.app.domain.model.Recipe

/** Pure helpers for recipe time / difficulty metadata (AI-research estimates). */
enum class TimeFilter(val label: String, val maxMinutes: Int?) {
    ALL("Tất cả", null),
    LE_15("≤15 phút", 15),
    LE_30("≤30 phút", 30),
    LE_60("≤60 phút", 60)
}

enum class DifficultyFilter(val label: String, val code: String?) {
    ALL("Tất cả", null),
    EASY("Dễ", "de"),
    MEDIUM("Trung bình", "trung_binh"),
    HARD("Khó", "kho")
}

fun difficultyLabel(code: String?): String? = when (code) {
    "de" -> "Dễ"
    "trung_binh" -> "Trung bình"
    "kho" -> "Khó"
    else -> null
}

/** prep + cook, null part counted as 0; null when both are null (unknown). */
fun totalMinutes(prep: Int?, cook: Int?): Int? =
    if (prep == null && cook == null) null else (prep ?: 0) + (cook ?: 0)

fun totalMinutes(recipe: Recipe): Int? = totalMinutes(recipe.prepTimeMinutes, recipe.cookTimeMinutes)

fun matchesTime(filter: TimeFilter, prep: Int?, cook: Int?): Boolean {
    val max = filter.maxMinutes ?: return true
    val total = totalMinutes(prep, cook) ?: return false
    return total <= max
}

fun matchesTime(filter: TimeFilter, recipe: Recipe): Boolean =
    matchesTime(filter, recipe.prepTimeMinutes, recipe.cookTimeMinutes)

fun matchesDifficulty(filter: DifficultyFilter, difficulty: String?): Boolean {
    val code = filter.code ?: return true
    return difficulty == code
}

fun matchesDifficulty(filter: DifficultyFilter, recipe: Recipe): Boolean =
    matchesDifficulty(filter, recipe.difficulty)

/** Hostname of a source URL without leading "www."; null when blank or unparsable. */
fun sourceHost(url: String?): String? {
    val trimmed = url?.trim().orEmpty()
    if (trimmed.isEmpty()) return null
    val afterScheme = trimmed.substringAfter("://", trimmed)
    val host = afterScheme.substringBefore('/').substringBefore('?').substringBefore('#')
        .substringAfterLast('@').substringBefore(':').lowercase()
    if (host.isEmpty() || !host.contains('.')) return null
    return host.removePrefix("www.")
}

/** Names only the fields actually missing; null when nothing is missing. */
fun missingFieldsNote(recipe: Recipe): String? {
    val missing = buildList {
        if (totalMinutes(recipe) == null) add("thời gian")
        if (difficultyLabel(recipe.difficulty) == null) add("độ khó")
        if (recipe.storageTips.isEmpty()) add("mẹo bảo quản")
    }
    if (missing.isEmpty()) return null
    return "Chưa có dữ liệu ${missing.joinToString(", ")}."
}

/** "Chuẩn bị ~X phút · Nấu ~Y phút · Độ khó: Dễ" using only present fields; null if none. */
fun metadataSummary(recipe: Recipe): String? {
    val parts = buildList {
        recipe.prepTimeMinutes?.let { add("Chuẩn bị ~$it phút") }
        recipe.cookTimeMinutes?.let { add("Nấu ~$it phút") }
        difficultyLabel(recipe.difficulty)?.let { add("Độ khó: $it") }
    }
    return if (parts.isEmpty()) null else parts.joinToString(" · ")
}

/** Source attribution for the estimates, e.g. "ước lượng, nguồn: example.com". */
fun metadataSourceNote(recipe: Recipe): String {
    val hosts = listOf(recipe.prepTimeSourceUrl, recipe.cookTimeSourceUrl, recipe.difficultySourceUrl)
        .mapNotNull { sourceHost(it) }.distinct()
    return if (hosts.isEmpty()) "ước lượng" else "ước lượng, nguồn: ${hosts.joinToString(", ")}"
}

/** "N món chưa có dữ liệu ... nên bị ẩn." or null when no relevant filter / none hidden. */
fun hiddenUnknownNote(recipes: List<Recipe>, time: TimeFilter, difficulty: DifficultyFilter): String? {
    val timeOn = time != TimeFilter.ALL
    val diffOn = difficulty != DifficultyFilter.ALL
    if (!timeOn && !diffOn) return null
    val n = recipes.count {
        (timeOn && totalMinutes(it) == null) || (diffOn && difficultyLabel(it.difficulty) == null)
    }
    if (n == 0) return null
    val what = when {
        timeOn && diffOn -> "thời gian/độ khó"
        timeOn -> "thời gian"
        else -> "độ khó"
    }
    return "$n món chưa có dữ liệu $what nên bị ẩn."
}

fun storageSourceNote(url: String?): String? {
    val host = sourceHost(url) ?: return null
    return if (host.endsWith("fda.gov")) "Nguồn: FDA (phạm vi công cộng)" else "Nguồn: $host"
}
