/** Recipe time/difficulty/storage helpers. Pure functions; values are AI-research estimates. */
export const TIME_LIMITS = [15, 30, 60];
export const DIFFICULTY_LABELS = { de: "Dễ", trung_binh: "Trung bình", kho: "Khó" };

const isMinutes = (value) => Number.isFinite(value) && value >= 0;

/** Total minutes (null part counts as 0); null when both parts are unknown. */
export function totalMinutes(recipe) {
  const prep = isMinutes(recipe?.prep_time_minutes) ? recipe.prep_time_minutes : null;
  const cook = isMinutes(recipe?.cook_time_minutes) ? recipe.cook_time_minutes : null;
  if (prep === null && cook === null) return null;
  return (prep || 0) + (cook || 0);
}

/** limit empty/null/0 = no filter. Unknown recipes never match an active limit. */
export function matchesTime(recipe, limit) {
  if (!limit) return true;
  const total = totalMinutes(recipe);
  return total !== null && total <= Number(limit);
}

export function matchesDifficulty(recipe, difficulty) {
  if (!difficulty) return true;
  return recipe?.difficulty === difficulty;
}

/** Apply both filters; reports how many recipes were hidden because data is unknown. */
export function filterByMetadata(recipes, { timeLimit = 0, difficulty = "" } = {}) {
  const list = recipes || [];
  if (!timeLimit && !difficulty) return { recipes: list, hiddenUnknown: 0 };
  let hiddenUnknown = 0;
  const kept = list.filter((recipe) => {
    if (timeLimit && totalMinutes(recipe) === null) { hiddenUnknown += 1; return false; }
    if (difficulty && !DIFFICULTY_LABELS[recipe?.difficulty]) { hiddenUnknown += 1; return false; }
    return matchesTime(recipe, timeLimit) && matchesDifficulty(recipe, difficulty);
  });
  return { recipes: kept, hiddenUnknown };
}

export function hiddenUnknownMessage(count, { timeLimit = 0, difficulty = "" } = {}) {
  if (!count || (!timeLimit && !difficulty)) return "";
  const what = timeLimit && difficulty ? "thời gian/độ khó" : timeLimit ? "thời gian" : "độ khó";
  return `${count} món chưa có dữ liệu ${what} nên bị ẩn.`;
}

export function hostnameOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/** "Chuẩn bị ~X phút · Nấu ~Y phút · Độ khó: Dễ" with only existing fields; "" when none. */
export function timeDifficultyLine(recipe) {
  const parts = [];
  if (isMinutes(recipe?.prep_time_minutes)) parts.push(`Chuẩn bị ~${recipe.prep_time_minutes} phút`);
  if (isMinutes(recipe?.cook_time_minutes)) parts.push(`Nấu ~${recipe.cook_time_minutes} phút`);
  if (DIFFICULTY_LABELS[recipe?.difficulty]) parts.push(`Độ khó: ${DIFFICULTY_LABELS[recipe.difficulty]}`);
  return parts.join(" · ");
}

export function estimateSourceLabel(recipe) {
  const hosts = [recipe?.prep_time_source_url, recipe?.cook_time_source_url, recipe?.difficulty_source_url]
    .map(hostnameOf).filter(Boolean);
  const host = hosts[0];
  return host ? `ước lượng, nguồn: ${host}` : "ước lượng";
}

export function storageTips(recipe) {
  return Array.isArray(recipe?.storage_tips) ? recipe.storage_tips.filter((t) => typeof t === "string" && t.trim()) : [];
}

export function storageSourceLabel(recipe) {
  const host = hostnameOf(recipe?.storage_source_url);
  return host.endsWith("fda.gov") ? "Nguồn: FDA (phạm vi công cộng)" : host ? `Nguồn: ${host}` : "";
}

/** Note naming only the metadata fields that are missing; "" when everything exists. */
export function missingMetadataNote(recipe) {
  const missing = [];
  if (totalMinutes(recipe) === null) missing.push("thời gian chuẩn bị/nấu");
  if (!DIFFICULTY_LABELS[recipe?.difficulty]) missing.push("độ khó");
  if (!storageTips(recipe).length) missing.push("mẹo bảo quản");
  if (!missing.length) return "";
  return `Danh mục chưa có ${missing.join(", ")} được xác minh cho công thức này.`;
}
