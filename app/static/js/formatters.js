/**
/**
 * Shared Date & Vietnamese formatting utilities for EasyMeals web client.
 */

const WEEKDAY_NAMES = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

export function formatDateVN(dateStr) {
  if (!dateStr) return "";
  const parts = dateStr.slice(0, 10).split("-");
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
}

export function formatRelativeDate(dateStr, baseDate) {
  if (!dateStr) return "";
  const d = new Date(dateStr.slice(0, 10) + "T00:00:00");
  const today = baseDate ? new Date(baseDate) : new Date();
  today.setHours(0, 0, 0, 0);

  const diffMs = d.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dow = WEEKDAY_NAMES[d.getDay()];

  if (diffDays === 0) return `Hôm nay, ${dd}/${mm}`;
  if (diffDays === 1) return `Ngày mai, ${dd}/${mm}`;
  if (diffDays === -1) return `Hôm qua, ${dd}/${mm}`;
  return `${dow} ${dd}/${mm}`;
}

export function formatExpiryStatus(dateStr, baseDate) {
  if (!dateStr) return null;
  const d = new Date(dateStr.slice(0, 10) + "T00:00:00");
  const today = baseDate ? new Date(baseDate) : new Date();
  today.setHours(0, 0, 0, 0);

  const diffMs = d.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  const formatted = formatDateVN(dateStr);

  if (diffDays < 0) {
    return {
      text: `Quá hạn ${Math.abs(diffDays)} ngày (${formatted})`,
      isWarning: true,
      isExpired: true,
      diffDays,
    };
  }
  if (diffDays === 0) {
    return {
      text: `Hết hạn hôm nay (${formatted})`,
      isWarning: true,
      isExpired: true,
      diffDays: 0,
    };
  }
  if (diffDays === 1) {
    return {
      text: `Hết hạn ngày mai (${formatted})`,
      isWarning: true,
      isExpired: false,
      diffDays: 1,
    };
  }
  if (diffDays === 2) {
    return {
      text: `Còn 2 ngày (${formatted})`,
      isWarning: true,
      isExpired: false,
      diffDays: 2,
    };
  }
  return {
    text: `Còn ${diffDays} ngày (${formatted})`,
    isWarning: false,
    isExpired: false,
    diffDays,
  };
}
