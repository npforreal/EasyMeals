import test from "node:test";
import assert from "node:assert/strict";
import {
  totalMinutes, matchesTime, matchesDifficulty, filterByMetadata, hiddenUnknownMessage,
  timeDifficultyLine, estimateSourceLabel, storageSourceLabel, missingMetadataNote, hostnameOf,
} from "../../app/static/js/recipe-metadata.js";

const r = (prep, cook, extra = {}) => ({ prep_time_minutes: prep, cook_time_minutes: cook, ...extra });

test("totalMinutes counts null part as 0 and both null as unknown", () => {
  assert.equal(totalMinutes(r(10, 20)), 30);
  assert.equal(totalMinutes(r(null, 20)), 20);
  assert.equal(totalMinutes(r(10, null)), 10);
  assert.equal(totalMinutes(r(null, null)), null);
  assert.equal(totalMinutes({}), null);
});

test("matchesTime boundaries and unknown exclusion", () => {
  assert.equal(matchesTime(r(5, 10), 15), true);
  assert.equal(matchesTime(r(5, 11), 15), false);
  assert.equal(matchesTime(r(15, 15), 30), true);
  assert.equal(matchesTime(r(30, 30), 60), true);
  assert.equal(matchesTime(r(30, 31), 60), false);
  assert.equal(matchesTime(r(null, 60), 60), true);
  assert.equal(matchesTime(r(null, 61), 60), false);
  assert.equal(matchesTime(r(null, null), 60), false);
  assert.equal(matchesTime(r(null, null), 0), true);
});

test("matchesDifficulty", () => {
  assert.equal(matchesDifficulty({ difficulty: "de" }, "de"), true);
  assert.equal(matchesDifficulty({ difficulty: "kho" }, "de"), false);
  assert.equal(matchesDifficulty({ difficulty: null }, "de"), false);
  assert.equal(matchesDifficulty({ difficulty: null }, ""), true);
});

test("filterByMetadata counts hidden unknown recipes", () => {
  const list = [r(5, 5, { difficulty: "de" }), r(null, null, { difficulty: "de" }), r(30, 30, { difficulty: null })];
  assert.equal(filterByMetadata(list, {}).hiddenUnknown, 0);
  const t = filterByMetadata(list, { timeLimit: 15 });
  assert.equal(t.recipes.length, 1);
  assert.equal(t.hiddenUnknown, 1);
  const d = filterByMetadata(list, { difficulty: "de" });
  assert.equal(d.recipes.length, 2);
  assert.equal(d.hiddenUnknown, 1);
  const both = filterByMetadata(list, { timeLimit: 60, difficulty: "de" });
  assert.equal(both.recipes.length, 1);
  assert.equal(both.hiddenUnknown, 2);
});

test("status wording", () => {
  assert.equal(hiddenUnknownMessage(3, { timeLimit: 15 }), "3 món chưa có dữ liệu thời gian nên bị ẩn.");
  assert.equal(hiddenUnknownMessage(2, { difficulty: "de" }), "2 món chưa có dữ liệu độ khó nên bị ẩn.");
  assert.equal(hiddenUnknownMessage(4, { timeLimit: 15, difficulty: "de" }), "4 món chưa có dữ liệu thời gian/độ khó nên bị ẩn.");
  assert.equal(hiddenUnknownMessage(0, { timeLimit: 15 }), "");
});

test("detail line and notes only mention existing/missing fields", () => {
  assert.equal(timeDifficultyLine(r(10, 20, { difficulty: "de" })), "Chuẩn bị ~10 phút · Nấu ~20 phút · Độ khó: Dễ");
  assert.equal(timeDifficultyLine(r(null, 20, { difficulty: null })), "Nấu ~20 phút");
  assert.equal(timeDifficultyLine({}), "");
  assert.equal(missingMetadataNote({}), "Danh mục chưa có thời gian chuẩn bị/nấu, độ khó, mẹo bảo quản được xác minh cho công thức này.");
  assert.equal(missingMetadataNote(r(1, 2, { difficulty: "kho", storage_tips: ["a"] })), "");
  assert.equal(missingMetadataNote(r(1, 2, { difficulty: "kho", storage_tips: [] })), "Danh mục chưa có mẹo bảo quản được xác minh cho công thức này.");
});

test("source labels use hostname only", () => {
  assert.equal(hostnameOf("https://www.example.com/a/b?x=1"), "example.com");
  assert.equal(hostnameOf("bad"), "");
  assert.equal(estimateSourceLabel(r(1, 2, { prep_time_source_url: "https://www.dienmayxanh.com/x/y" })), "ước lượng, nguồn: dienmayxanh.com");
  assert.equal(storageSourceLabel({ storage_source_url: "https://www.fda.gov/food/a" }), "Nguồn: FDA (phạm vi công cộng)");
  assert.equal(storageSourceLabel({}), "");
});
