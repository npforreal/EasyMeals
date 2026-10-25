import test from "node:test";
import assert from "node:assert/strict";
import {
  formatDateVN,
  formatRelativeDate,
  formatExpiryStatus,
} from "../../app/static/js/formatters.js";

test("formatDateVN formats correctly", () => {
  assert.equal(formatDateVN("2026-10-25"), "25/10/2026");
});

test("formatRelativeDate handles today, tomorrow, day of week", () => {
  const base = new Date("2026-10-25T00:00:00");
  assert.equal(formatRelativeDate("2026-10-25", base), "Hôm nay, 25/10");
  assert.equal(formatRelativeDate("2026-10-26", base), "Ngày mai, 26/10");
  assert.equal(formatRelativeDate("2026-10-24", base), "Hôm qua, 24/10");
  assert.equal(formatRelativeDate("2026-10-27", base), "T3 27/10");
});

test("formatExpiryStatus flags warning <= 2 days or expired", () => {
  const base = new Date("2026-10-25T00:00:00");
  const exp0 = formatExpiryStatus("2026-10-25", base);
  assert.equal(exp0.isWarning, true);
  assert.equal(exp0.isExpired, true);

  const exp1 = formatExpiryStatus("2026-10-26", base);
  assert.equal(exp1.isWarning, true);
  assert.equal(exp1.isExpired, false);
  assert.match(exp1.text, /ngày mai/i);

  const exp2 = formatExpiryStatus("2026-10-27", base);
  assert.equal(exp2.isWarning, true);

  const exp3 = formatExpiryStatus("2026-10-28", base);
  assert.equal(exp3.isWarning, false);

  const expPast = formatExpiryStatus("2026-10-23", base);
  assert.equal(expPast.isWarning, true);
  assert.equal(expPast.isExpired, true);
  assert.match(expPast.text, /quá hạn 2 ngày/i);
});
