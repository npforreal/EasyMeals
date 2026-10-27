/**
 * EasyMeals — Main Client Application Controller.
 *
 * Architecture:
 * - Personal Data stored locally in IndexedDB (pantry, plans, movements, settings).
 * - Shared Catalogue read-only via public API & cached in IndexedDB.
 * - Stateless API computation for plan generation and stock deductions.
 * - Secure-by-default: textContent DOM rendering, zero raw innerHTML on dynamic data.
 */

import {
  openDB,
  clearAllPersonalData,
  requestStoragePersistence,
} from "./js/db.js";
import {
  getPantryLots,
  getLocalSetting,
  setLocalSetting,
  addPantryLot,
  toApiPantryLots,
  mergeLocalPrices,
  updatePantryLot,
  deletePantryLot,
  getMealPlans,
  saveMealPlans,
  deleteMealPlansByIds,
  executeEatMealAtomic,
  executeUndoEatMealAtomic,
  getStockMovements,
  getHistorySummary,
  normalizeBackupPayload,
  getCachedCatalogue,
  syncCatalogue,
  exportBackupJSON,
  validateBackupJSON,
  importBackupJSON,
  getShoppingItems,
  addShoppingItem,
  replacePlanShoppingItems,
  toggleShoppingItemBought,
  updateShoppingItem,
  deleteShoppingItemsByIds,
  clearBoughtShoppingItems,
  executeBoughtToPantryAtomic,
  defaultExpiryDate,
  resolveIngredientCategory,
  CATALOGUE_SOURCE,
  SHOPPING_SOURCE_MANUAL,
  mergeShoppingItems,
} from "./js/storage.js";
import {
  generatePeriodPlan as engineGeneratePeriodPlan,
  mergeNewPlansIntoExisting as engineMergeNewPlansIntoExisting,
  regenerateSingleMeal as engineRegenerateSingleMeal,
  recomputeShoppingList as engineRecomputeShoppingList,
  calculateShoppingBudget as engineCalculateShoppingBudget,
  groupShoppingItemsByCategory as engineGroupShoppingItemsByCategory,
  swapDishInMeal as engineSwapDishInMeal,
  addDishToMeal as engineAddDishToMeal,
  removeDishFromMeal as engineRemoveDishFromMeal,
  rescheduleMeal as engineRescheduleMeal,
  mergeCompatibleShoppingItems as engineMergeCompatibleShoppingItems,
  deductRecipeStockFifo as engineDeductRecipeStockFifo,
  deductRecipeStockAvailable as engineDeductRecipeStockAvailable,
  reverseStockMovements as engineReverseStockMovements,
  getTotalIngredientStock as engineGetTotalIngredientStock,
} from "./js/engine.js";
import { filterRecipesByPreferences, filterRecipesForBrowse } from "./js/recipe-preferences.js";
import {
  filterByMetadata, hiddenUnknownMessage, timeDifficultyLine, estimateSourceLabel,
  storageTips, storageSourceLabel, missingMetadataNote,
} from "./js/recipe-metadata.js";
import {
  formatDateVN,
  formatRelativeDate,
  formatExpiryStatus,
} from "./js/formatters.js";
import {
  LEFTOVER_DEFAULT_DAYS,
  LEFTOVER_MAX_DAYS,
  LEFTOVER_MIN_DAYS,
  PLAN_MIN_DAYS,
  PLAN_MAX_DAYS,
  PLAN_DEFAULT_DAYS,
} from "./js/constants.js";

// ==========================================
// Toast & Utility Helpers
// ==========================================

export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

export function formatQty(num) {
  const n = parseFloat(num);
  if (isNaN(n)) return "0";
  return Number.isInteger(n) ? n.toString() : n.toFixed(1);
}

export function sensibleDefaultQuantity(ing) {
  const unit = ing.default_unit || "g";
  const cat = ing.category || "khac";
  const name = (ing.name || "").toLowerCase();
  switch (unit) {
    case "piece":
      if (name.includes("trứng")) return "6";
      if (name.includes("đậu hũ") || name.includes("tàu hũ")) return "2";
      return "1";
    case "kg":
    case "l":
      return "1";
    case "ml":
      return cat === "nuoc_cham_dau" ? "100" : "200";
    default:
      switch (cat) {
        case "thit":
        case "gia_cam":
        case "hai_san":
          return "400";
        case "rau_cu":
        case "cu_qua":
          return "300";
        case "gao_bot_mi":
          return "500";
        case "gia_vi":
          return "30";
        case "nuoc_cham_dau":
          return "100";
        default:
          return "200";
      }
  }
}

const CAT_LABELS = { man: "Món Mặn", rau: "Món Rau", canh: "Món Canh" };
const PERIOD_LABELS = { breakfast: "Bữa Sáng", lunch: "Bữa Trưa", dinner: "Bữa Tối" };

// ==========================================
// G3 — Modal/Dialog accessibility
// ==========================================
// Đưa focus vào hộp thoại, giữ Tab trong hộp thoại, đóng bằng Escape và trả
// focus về nút đã mở. Chỉ một hộp thoại hoạt động tại một thời điểm.
const DIALOG_FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
let activeDialog = null;

function isElementVisible(el) {
  return !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
}

export function activateDialog(overlay, { onEscape = null, initialFocus = null } = {}) {
  if (!overlay) return () => {};
  if (activeDialog && activeDialog.overlay === overlay) return activeDialog.deactivate;

  if (activeDialog) activeDialog.deactivate({ restoreFocus: false });
  const previous = document.activeElement;
  const modal = overlay.querySelector(".modal") || overlay;
  if (!modal.hasAttribute("role")) modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  if (!modal.hasAttribute("tabindex")) modal.setAttribute("tabindex", "-1");

  const focusables = () => Array.from(modal.querySelectorAll(DIALOG_FOCUSABLE)).filter(isElementVisible);

  const onKeydown = (event) => {
    if (!isElementVisible(overlay)) return;
    if (event.key === "Escape") {
      event.preventDefault();
      if (onEscape) onEscape();
      else overlay.dispatchEvent(new CustomEvent("dialog:cancel"));
      return;
    }
    if (event.key !== "Tab") return;
    const items = focusables();
    if (!items.length) {
      event.preventDefault();
      modal.focus();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const current = document.activeElement;
    if (event.shiftKey && (current === first || current === modal || !modal.contains(current))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (current === last || !modal.contains(current))) {
      event.preventDefault();
      first.focus();
    }
  };

  const deactivate = ({ restoreFocus = true } = {}) => {
    document.removeEventListener("keydown", onKeydown, true);
    if (activeDialog && activeDialog.overlay === overlay) activeDialog = null;
    if (restoreFocus && previous && typeof previous.focus === "function" && document.contains(previous)) {
      previous.focus({ preventScroll: true });
    }
  };

  activeDialog = { overlay, deactivate };
  document.addEventListener("keydown", onKeydown, true);

  const target = initialFocus && isElementVisible(initialFocus) ? initialFocus : focusables()[0] || modal;
  // Chờ một nhịp để trình duyệt hiển thị overlay trước khi đặt focus.
  setTimeout(() => {
    if (document.contains(target)) target.focus({ preventScroll: true });
  }, 0);
  return deactivate;
}

export function deactivateDialog(overlay) {
  if (activeDialog && (!overlay || activeDialog.overlay === overlay)) {
    activeDialog.deactivate();
    return true;
  }
  return false;
}

// ==========================================
// Recipe Modal & Cooking Mode
// ==========================================

export function startCookingMode(recipe) {
  let overlay = document.getElementById("cooking-mode-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "cooking-mode-overlay";
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100vw";
    overlay.style.height = "100vh";
    overlay.style.zIndex = "9999";
    overlay.style.background = "var(--surface)";
    overlay.style.display = "flex";
    overlay.style.flexDirection = "column";
    overlay.style.padding = "var(--space-4)";
    document.body.appendChild(overlay);
  }
  overlay.style.display = "flex";
  let step = 0;
  let servings = recipe.servings || 4;
  const checkedIngredients = new Set();
  const steps = recipe.instructions || [];
  const keepAwakeKey = "easymeals_keep_screen_on";
  let keepAwake = localStorage.getItem(keepAwakeKey) !== "false";

  let wakeLock = null;
  if (keepAwake && "wakeLock" in navigator) {
    navigator.wakeLock.request("screen").then((wl) => { wakeLock = wl; }).catch(() => {});
  }

  function renderStep() {
    overlay.innerHTML = "";

    const topBar = document.createElement("div");
    topBar.style.display = "flex";
    topBar.style.justifyContent = "space-between";
    topBar.style.alignItems = "center";
    topBar.style.borderBottom = "1px solid var(--border)";
    topBar.style.paddingBottom = "var(--space-3)";

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn btn-outline btn-sm";
    closeBtn.textContent = "Thoát chế độ nấu";
    closeBtn.addEventListener("click", () => {
      if (wakeLock) { wakeLock.release(); wakeLock = null; }
      overlay.style.display = "none";
    });

    const modeLabel = document.createElement("span");
    modeLabel.style.fontWeight = "bold";
    modeLabel.style.color = "var(--accent)";
    modeLabel.textContent = "CHẾ ĐỘ NẤU";

    const stepCounter = document.createElement("span");
    stepCounter.style.fontWeight = "bold";
    stepCounter.textContent = `${steps.length ? step + 1 : 1} / ${steps.length || 1}`;

    topBar.appendChild(closeBtn);
    topBar.appendChild(modeLabel);
    topBar.appendChild(stepCounter);
    overlay.appendChild(topBar);

    const settings = document.createElement("div");
    settings.style.display = "flex";
    settings.style.justifyContent = "space-between";
    settings.style.gap = "var(--space-3)";
    const servingsLabel = document.createElement("label");
    servingsLabel.textContent = "Khẩu phần ";
    const servingsInput = document.createElement("input");
    servingsInput.type = "number";
    servingsInput.min = "1";
    servingsInput.max = "20";
    servingsInput.value = String(servings);
    servingsInput.setAttribute("aria-label", "Số khẩu phần");
    servingsInput.addEventListener("change", () => {
      servings = Math.max(1, Math.min(20, Number(servingsInput.value) || 1));
      renderStep();
    });
    servingsLabel.appendChild(servingsInput);
    const awakeLabel = document.createElement("label");
    const awakeCheckbox = document.createElement("input");
    awakeCheckbox.type = "checkbox";
    awakeCheckbox.checked = keepAwake;
    awakeCheckbox.addEventListener("change", async () => {
      keepAwake = awakeCheckbox.checked;
      localStorage.setItem(keepAwakeKey, String(keepAwake));
      if (!keepAwake && wakeLock) { await wakeLock.release(); wakeLock = null; }
      if (keepAwake && "wakeLock" in navigator) {
        try { wakeLock = await navigator.wakeLock.request("screen"); } catch { /* The platform may deny a wake lock. */ }
      }
    });
    awakeLabel.append(awakeCheckbox, document.createTextNode(" Giữ màn hình sáng"));
    settings.append(servingsLabel, awakeLabel);
    overlay.appendChild(settings);

    const ingredientsList = document.createElement("ul");
    ingredientsList.style.maxHeight = "24vh";
    ingredientsList.style.overflowY = "auto";
    ingredientsList.setAttribute("aria-label", "Checklist nguyên liệu");
    const ingredientsHeading = document.createElement("h3");
    ingredientsHeading.textContent = "Checklist nguyên liệu";
    ingredientsHeading.style.margin = "var(--space-2) 0";
    overlay.appendChild(ingredientsHeading);
    (recipe.ingredients || []).forEach((ingredient) => {
      const item = document.createElement("li");
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = checkedIngredients.has(ingredient.ingredient_id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) checkedIngredients.add(ingredient.ingredient_id);
        else checkedIngredients.delete(ingredient.ingredient_id);
      });
      const quantity = Number(ingredient.quantity) * servings / (recipe.servings || 4);
      label.append(checkbox, document.createTextNode(` ${ingredient.ingredient_name}: ${formatQty(quantity)} ${ingredient.unit}`));
      item.appendChild(label);
      ingredientsList.appendChild(item);
    });
    overlay.appendChild(ingredientsList);

    const midBox = document.createElement("div");
    midBox.style.flex = "1";
    midBox.style.display = "flex";
    midBox.style.flexDirection = "column";
    midBox.style.justifyContent = "center";
    midBox.style.alignItems = "center";
    midBox.style.textAlign = "center";
    midBox.style.padding = "var(--space-6)";

    const titleH2 = document.createElement("h2");
    titleH2.style.marginBottom = "var(--space-2)";
    titleH2.textContent = recipe.name;

    const stepText = document.createElement("div");
    stepText.style.fontSize = "1.4rem";
    stepText.style.lineHeight = "1.6";
    stepText.style.margin = "var(--space-4) 0";
    stepText.style.maxWidth = "600px";
    stepText.textContent = steps[step] || "Không có hướng dẫn chi tiết.";

    midBox.appendChild(titleH2);
    midBox.appendChild(stepText);
    overlay.appendChild(midBox);

    const bottomBar = document.createElement("div");
    bottomBar.style.display = "flex";
    bottomBar.style.gap = "var(--space-3)";
    bottomBar.style.borderTop = "1px solid var(--border)";
    bottomBar.style.paddingTop = "var(--space-3)";

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "btn btn-outline";
    prevBtn.style.flex = "1";
    prevBtn.textContent = "Bước trước";
    prevBtn.disabled = step === 0;
    prevBtn.addEventListener("click", () => {
      if (step > 0) { step--; renderStep(); }
    });

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "btn btn-primary";
    nextBtn.style.flex = "1";
    nextBtn.textContent = step >= steps.length - 1 ? "Hoàn thành" : "Bước tiếp theo";
    nextBtn.addEventListener("click", () => {
      if (step < steps.length - 1) {
        step++;
        renderStep();
      } else {
        if (wakeLock) { wakeLock.release(); wakeLock = null; }
        overlay.style.display = "none";
        showToast("Đã hoàn thành nấu món ăn!", "success");
      }
    });

    bottomBar.appendChild(prevBtn);
    bottomBar.appendChild(nextBtn);
    overlay.appendChild(bottomBar);
  }

  renderStep();
}

export function showDeficitDialog(deficitsList, onEatPartial, onAddToShopping) {
  let dlgOverlay = document.getElementById("deficit-modal-overlay");
  if (!dlgOverlay) {
    dlgOverlay = document.createElement("div");
    dlgOverlay.id = "deficit-modal-overlay";
    dlgOverlay.className = "modal-overlay";
    dlgOverlay.style.zIndex = "9998";
    dlgOverlay.innerHTML = `
      <div class="modal" style="max-width: 480px; padding: var(--space-4);">
        <h3 style="margin-top: 0; color: var(--danger);">Không đủ nguyên liệu</h3>
        <p>Bữa ăn còn thiếu các nguyên liệu sau trong kho:</p>
        <ul id="deficit-list" style="padding-left: var(--space-4); margin: var(--space-3) 0;"></ul>
        <p style="margin-bottom: var(--space-4);">Bạn muốn xử lý thế nào?</p>
        <div style="display: flex; flex-direction: column; gap: var(--space-2);">
          <button type="button" class="btn btn-primary" id="btn-add-shopping">Thêm phần thiếu vào danh sách đi chợ</button>
          <button type="button" class="btn btn-outline" id="btn-eat-partial">Vẫn đánh dấu đã ăn (trừ phần đang có)</button>
          <button type="button" class="btn btn-outline" id="btn-cancel-deficit">Huỷ</button>
        </div>
      </div>
    `;
    document.body.appendChild(dlgOverlay);
  }
  const ul = dlgOverlay.querySelector("#deficit-list");
  ul.innerHTML = "";
  deficitsList.forEach((d) => {
    const li = document.createElement("li");
    li.style.color = "var(--danger)";
    li.textContent = `• ${d.name}: thiếu ${formatQty(d.missing)} ${d.unit}`;
    ul.appendChild(li);
  });
  dlgOverlay.style.display = "flex";

  const closeDlg = () => {
    dlgOverlay.style.display = "none";
    deactivateDialog(dlgOverlay);
  };
  activateDialog(dlgOverlay, { onEscape: closeDlg });
  dlgOverlay.querySelector("#btn-cancel-deficit").onclick = closeDlg;
  dlgOverlay.querySelector("#btn-add-shopping").onclick = () => {
    onAddToShopping();
    closeDlg();
  };
  dlgOverlay.querySelector("#btn-eat-partial").onclick = () => {
    onEatPartial();
    closeDlg();
  };
}

/**
 * Hộp thoại giữ/thay khi tạo thực đơn mới trùng ngày bữa chưa ăn (A2 - Vòng 13).
 * Trả về Promise: "replace" (Thay các bữa chưa ăn trong khoảng ngày này),
 * "keep" (Giữ thực đơn cũ, chỉ thêm ngày chưa có) hoặc null (Huỷ).
 */
export function askPlanConflictChoice() {
  return new Promise((resolve) => {
    const old = document.getElementById("plan-conflict-overlay");
    if (old) old.remove();

    const overlay = document.createElement("div");
    overlay.id = "plan-conflict-overlay";
    overlay.className = "modal-overlay";
    overlay.style.zIndex = "9998";

    const modal = document.createElement("div");
    modal.className = "modal";
    modal.style.maxWidth = "480px";
    modal.style.padding = "var(--space-4)";

    const title = document.createElement("h3");
    title.style.marginTop = "0";
    title.textContent = "Thực đơn mới trùng ngày với bữa chưa ăn";
    modal.appendChild(title);

    const body = document.createElement("p");
    body.textContent = "Bạn muốn xử lý thế nào? Các bữa đã ăn luôn được giữ cùng lịch sử kho.";
    modal.appendChild(body);

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;flex-direction:column;gap:var(--space-2);";

    const btnReplace = document.createElement("button");
    btnReplace.type = "button";
    btnReplace.id = "btn-replace-plans";
    btnReplace.className = "btn btn-primary";
    btnReplace.textContent = "Thay các bữa chưa ăn trong khoảng ngày này";
    actions.appendChild(btnReplace);

    const btnKeep = document.createElement("button");
    btnKeep.type = "button";
    btnKeep.id = "btn-keep-plans";
    btnKeep.className = "btn btn-outline";
    btnKeep.textContent = "Giữ thực đơn cũ, chỉ thêm ngày chưa có";
    actions.appendChild(btnKeep);

    const btnCancel = document.createElement("button");
    btnCancel.type = "button";
    btnCancel.id = "btn-cancel-plans";
    btnCancel.className = "btn btn-outline";
    btnCancel.textContent = "Huỷ";
    actions.appendChild(btnCancel);

    modal.appendChild(actions);
    overlay.appendChild(modal);
    overlay.style.display = "flex";
    document.body.appendChild(overlay);
    activateDialog(overlay, { onEscape: () => close(null) });

    const close = (value) => {
      deactivateDialog(overlay);
      overlay.remove();
      resolve(value);
    };
    btnReplace.onclick = () => close("replace");
    btnKeep.onclick = () => close("keep");
    btnCancel.onclick = () => close(null);
  });
}

export async function addDeficitsToShoppingList(deficits) {
  for (const d of deficits) {
    await addShoppingItem(
      {
        // id thiếu (nguyên liệu tuỳ nhập) -> sinh mã duy nhất để không trùng key.
        ingredient_id: d.ingredient_id || d.id || ("custom_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8)),
        ingredient_name: d.ingredient_name || d.name,
        needed_quantity: String(d.missing_quantity || d.missing || d.quantity || "200"),
        unit: d.unit || "g",
      },
      { source: "manual" } // người dùng tự bấm thêm -> giữ khi kế hoạch đổi (A3)
    );
  }
}

export async function openRecipeModal(recipeId, initialServings = null) {
  const modalOverlay = document.getElementById("recipe-modal-overlay");
  const modalContent = document.getElementById("recipe-modal-content");
  if (!modalOverlay || !modalContent) return;

  modalContent.innerHTML = "";
  const loadingP = document.createElement("p");
  loadingP.textContent = "Đang tải công thức...";
  modalContent.appendChild(loadingP);
  modalOverlay.style.display = "flex";
  activateDialog(modalOverlay, { onEscape: closeRecipeModal });

  try {
    let recipe = null;
    const catalogue = await getCachedCatalogue();
    if (catalogue && catalogue.recipes) {
      recipe = catalogue.recipes.find((r) => r.id === recipeId);
    }

    if (!recipe) {
      const res = await fetch(`/api/recipes/${encodeURIComponent(recipeId)}`);
      if (!res.ok) throw new Error("Không thể tải công thức từ máy chủ.");
      recipe = await res.json();
    }

    const currentLots = await getPantryLots();
    const conversions = catalogue?.conversions || [];
    let curServings = initialServings || recipe.servings || 4;

    function renderModalBody() {
      modalContent.innerHTML = "";

      // Header
      const header = document.createElement("div");
      header.className = "modal-header";
      const titleBox = document.createElement("div");
      const h2 = document.createElement("h2");
      h2.textContent = recipe.name;
      const badge = document.createElement("span");
      badge.className = `badge badge-${recipe.category}`;
      badge.textContent = CAT_LABELS[recipe.category] || recipe.category;

      titleBox.appendChild(h2);
      titleBox.appendChild(badge);

      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "btn btn-outline btn-sm";
      closeBtn.textContent = "Đóng";
      closeBtn.addEventListener("click", closeRecipeModal);

      header.appendChild(titleBox);
      header.appendChild(closeBtn);
      modalContent.appendChild(header);

      // Portions Stepper
      const stepperRow = document.createElement("div");
      stepperRow.style.display = "flex";
      stepperRow.style.alignItems = "center";
      stepperRow.style.justifyContent = "space-between";
      stepperRow.style.padding = "var(--space-2) var(--space-3)";
      stepperRow.style.background = "var(--surface-variant)";
      stepperRow.style.borderRadius = "var(--radius-sm)";
      stepperRow.style.margin = "var(--space-3) 0";

      const stepperLeft = document.createElement("div");
      const strongTitle = document.createElement("strong");
      strongTitle.textContent = "Khẩu phần ăn";
      const subNote = document.createElement("div");
      subNote.style.fontSize = "0.8rem";
      subNote.style.color = "var(--text-muted)";
      subNote.textContent = "Tự động tính lại định lượng nguyên liệu";
      stepperLeft.appendChild(strongTitle);
      stepperLeft.appendChild(subNote);

      const stepperControls = document.createElement("div");
      stepperControls.style.display = "flex";
      stepperControls.style.alignItems = "center";
      stepperControls.style.gap = "var(--space-2)";

      const decBtn = document.createElement("button");
      decBtn.type = "button";
      decBtn.className = "btn btn-outline btn-sm";
      decBtn.textContent = "-";
      decBtn.disabled = curServings <= 1;
      decBtn.addEventListener("click", () => {
        if (curServings > 1) {
          curServings--;
          renderModalBody();
        }
      });

      const sSpan = document.createElement("span");
      sSpan.style.fontWeight = "bold";
      sSpan.style.minWidth = "2.5rem";
      sSpan.style.textAlign = "center";
      sSpan.textContent = `${curServings} người`;

      const incBtn = document.createElement("button");
      incBtn.type = "button";
      incBtn.className = "btn btn-outline btn-sm";
      incBtn.textContent = "+";
      incBtn.disabled = curServings >= 20;
      incBtn.addEventListener("click", () => {
        if (curServings < 20) {
          curServings++;
          renderModalBody();
        }
      });

      stepperControls.appendChild(decBtn);
      stepperControls.appendChild(sSpan);
      stepperControls.appendChild(incBtn);

      stepperRow.appendChild(stepperLeft);
      stepperRow.appendChild(stepperControls);
      modalContent.appendChild(stepperRow);

      // Body
      const body = document.createElement("div");

      const ingTitle = document.createElement("h3");
      ingTitle.style.fontSize = "1rem";
      ingTitle.style.marginBottom = "0.5rem";
      ingTitle.textContent = "Nguyên liệu cần chuẩn bị:";
      body.appendChild(ingTitle);

      const ingList = document.createElement("ul");
      ingList.style.listStyle = "none";
      ingList.style.padding = "0";
      ingList.style.display = "flex";
      ingList.style.flexDirection = "column";
      ingList.style.gap = "var(--space-2)";
      ingList.style.marginBottom = "var(--space-4)";

      const factor = curServings / (recipe.servings || 4);

      (recipe.ingredients || []).forEach((i) => {
        const scaledQty = parseFloat(i.quantity) * factor;
        const available = engineGetTotalIngredientStock(currentLots, i.ingredient_id, i.unit, conversions);
        const hasEnough = available >= scaledQty;
        const isPartial = available > 0 && available < scaledQty;

        const li = document.createElement("li");
        li.style.display = "flex";
        li.style.justifyContent = "space-between";
        li.style.alignItems = "center";
        li.style.padding = "var(--space-2)";
        li.style.borderRadius = "var(--radius-sm)";
        li.style.background = "var(--surface)";
        li.style.border = "1px solid var(--border)";

        const nameBox = document.createElement("div");
        const ingStrong = document.createElement("strong");
        ingStrong.textContent = `• ${i.ingredient_name}`;
        nameBox.appendChild(ingStrong);

        const statusNote = document.createElement("div");
        statusNote.style.fontSize = "0.75rem";
        if (hasEnough) {
          statusNote.style.color = "var(--primary)";
          statusNote.textContent = `✓ Có sẵn trong tủ (${formatQty(available)} ${i.unit})`;
        } else if (isPartial) {
          statusNote.style.color = "var(--accent)";
          statusNote.textContent = `⚠ Có ${formatQty(available)}, thiếu ${formatQty(scaledQty - available)} ${i.unit}`;
        } else {
          statusNote.style.color = "var(--danger)";
          statusNote.textContent = "✗ Chưa có trong tủ";
        }
        nameBox.appendChild(statusNote);

        const qtyBox = document.createElement("span");
        qtyBox.style.fontWeight = "bold";
        qtyBox.style.color = hasEnough ? "var(--primary)" : "var(--text)";
        qtyBox.textContent = `${formatQty(scaledQty)} ${i.unit}`;

        li.appendChild(nameBox);
        li.appendChild(qtyBox);
        ingList.appendChild(li);
      });
      body.appendChild(ingList);

      const metaLine = timeDifficultyLine(recipe);
      if (metaLine) {
        const metaP = document.createElement("p");
        metaP.id = "recipe-time-line";
        const metaStrong = document.createElement("strong");
        metaStrong.textContent = metaLine;
        const metaSrc = document.createElement("span");
        metaSrc.className = "text-muted";
        metaSrc.textContent = ` (${estimateSourceLabel(recipe)})`;
        metaP.appendChild(metaStrong);
        metaP.appendChild(metaSrc);
        body.appendChild(metaP);
      }
      const tips = storageTips(recipe);
      if (tips.length) {
        const tipsTitle = document.createElement("h3");
        tipsTitle.style.fontSize = "1rem";
        tipsTitle.style.marginBottom = "0.5rem";
        tipsTitle.textContent = "Mẹo bảo quản";
        const tipsList = document.createElement("ul");
        tipsList.id = "recipe-storage-tips";
        tips.forEach((tip) => {
          const tipLi = document.createElement("li");
          tipLi.textContent = tip;
          tipsList.appendChild(tipLi);
        });
        body.appendChild(tipsTitle);
        body.appendChild(tipsList);
        const tipsSrc = storageSourceLabel(recipe);
        if (tipsSrc) {
          const tipsSrcP = document.createElement("p");
          tipsSrcP.className = "text-muted";
          tipsSrcP.textContent = tipsSrc;
          body.appendChild(tipsSrcP);
        }
      }
      const missingNote = missingMetadataNote(recipe);
      if (missingNote) {
        const metadataNote = document.createElement("p");
        metadataNote.className = "text-muted";
        metadataNote.id = "recipe-metadata-missing";
        metadataNote.textContent = missingNote;
        body.appendChild(metadataNote);
      }

      const stepTitle = document.createElement("h3");
      stepTitle.style.fontSize = "1rem";
      stepTitle.style.marginBottom = "0.5rem";
      stepTitle.textContent = "Hướng dẫn các bước nấu:";
      body.appendChild(stepTitle);

      const stepList = document.createElement("ol");
      stepList.style.listStyle = "none";
      stepList.style.padding = "0";
      stepList.style.fontSize = "0.95rem";
      stepList.style.display = "flex";
      stepList.style.flexDirection = "column";
      stepList.style.gap = "0.5rem";
      stepList.style.marginBottom = "var(--space-4)";

      (recipe.instructions || []).forEach((step, idx) => {
        const li = document.createElement("li");
        const num = document.createElement("span");
        num.className = "step-num";
        num.style.fontWeight = "bold";
        num.style.color = "var(--primary)";
        num.style.marginRight = "6px";
        num.textContent = `${idx + 1}.`;
        li.appendChild(num);
        li.appendChild(document.createTextNode(step));
        stepList.appendChild(li);
      });
      body.appendChild(stepList);

      // Cooking Mode Button
      const cookBtn = document.createElement("button");
      cookBtn.type = "button";
      cookBtn.className = "btn btn-primary";
      cookBtn.style.width = "100%";
      cookBtn.textContent = "Bật chế độ nấu";
      cookBtn.addEventListener("click", () => {
        startCookingMode(recipe);
      });
      body.appendChild(cookBtn);

      modalContent.appendChild(body);
    }

    renderModalBody();
  } catch (err) {
    modalContent.innerHTML = "";
    const p = document.createElement("p");
    p.style.color = "var(--danger)";
    p.textContent = `Lỗi: ${err.message}`;
    modalContent.appendChild(p);
  }
}

export function closeRecipeModal() {
  const modalOverlay = document.getElementById("recipe-modal-overlay");
  if (modalOverlay) {
    modalOverlay.style.display = "none";
    deactivateDialog(modalOverlay);
  }
}

// ==========================================
// Ingredient Autocomplete
// ==========================================

function setupAutocomplete(inputId, dropdownId, hiddenId) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  const hidden = document.getElementById(hiddenId);
  if (!input || !dropdown || !hidden) return;

  let timer = null;

  // Trên điện thoại bàn phím ảo chiếm nửa màn hình: cuộn ô gõ lên cao nếu danh sách không đủ chỗ
  // và giới hạn chiều cao danh sách theo phần màn hình còn nhìn thấy.
  function fitDropdown() {
    const vv = window.visualViewport;
    let viewH = vv ? vv.height : window.innerHeight;
    // Thanh tab dưới (di động) là lớp cố định che phần đáy màn hình: coi nó là mép dưới vùng nhìn thấy.
    const tabbar = document.querySelector(".tabbar");
    if (tabbar && getComputedStyle(tabbar).display !== "none") {
      viewH = Math.min(viewH, tabbar.getBoundingClientRect().top);
    }
    let rect = input.getBoundingClientRect();
    if (viewH - rect.bottom < 180) {
      window.scrollBy({ top: rect.top - 72 });
      rect = input.getBoundingClientRect();
    }
    const room = viewH - rect.bottom - 16;
    dropdown.style.maxHeight = `${Math.max(132, Math.min(300, room))}px`;
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (!q) {
      dropdown.style.display = "none";
      hidden.value = "";
      return;
    }

    timer = setTimeout(async () => {
      try {
        let items = [];
        // Check local catalogue cache first
        let cached = await getCachedCatalogue();
        if (!cached && (CATALOGUE_SOURCE === "bundled" || !navigator.onLine)) {
          await syncCatalogue().catch(() => {});
          cached = await getCachedCatalogue();
        }

        if (cached && cached.ingredients) {
          const normQ = q.toLowerCase();
          items = cached.ingredients.filter(
            (i) =>
              i.name.toLowerCase().includes(normQ) ||
              (i.normalized_name && i.normalized_name.includes(normQ)) ||
              (i.aliases && i.aliases.some((a) => a.toLowerCase().includes(normQ)))
          );
        }

        // If nothing in cache or offline cache empty, fetch from API
        if (!items.length) {
          const res = await fetch(`/api/ingredients?q=${encodeURIComponent(q)}`);
          if (res.ok) {
            items = await res.json();
          }
        }

        dropdown.innerHTML = "";
        if (!items.length) {
          const empty = document.createElement("div");
          empty.className = "autocomplete-item autocomplete-item-empty";
          empty.textContent = "Không tìm thấy nguyên liệu chuẩn";
          dropdown.appendChild(empty);
          dropdown.style.display = "block";
          fitDropdown();
          return;
        }

        items.slice(0, 8).forEach((item) => {
          const el = document.createElement("div");
          el.className = "autocomplete-item";
          const strong = document.createElement("strong");
          strong.textContent = item.name;
          el.appendChild(strong);
          if (item.aliases && item.aliases.length) {
            const alias = document.createElement("span");
            alias.style.fontSize = "0.75rem";
            alias.style.color = "var(--ink-muted)";
            alias.style.marginLeft = "4px";
            alias.textContent = `(${item.aliases.join(", ")})`;
            el.appendChild(alias);
          }

          // Chọn khi nhả tay (click), KHÔNG chọn lúc chạm xuống: nếu không, vuốt để cuộn danh sách
          // sẽ chọn nhầm mục đầu tiên chạm phải. mousedown chỉ giữ focus ô gõ, không chặn cuộn cảm ứng.
          el.addEventListener("mousedown", (e) => e.preventDefault());
          el.addEventListener("click", (e) => {
            e.preventDefault();
            hidden.value = item.id;
            input.value = item.name;
            dropdown.style.display = "none";

            const unitSelect = document.getElementById("lot-unit");
            const qtyInput = document.getElementById("lot-quantity");
            if (unitSelect && item.default_unit) {
              unitSelect.value = item.default_unit;
            }
            if (qtyInput) {
              qtyInput.value = sensibleDefaultQuantity(item);
            }
          });
          dropdown.appendChild(el);
        });
        dropdown.style.display = "block";
        fitDropdown();
      } catch (e) {
        console.warn("Autocomplete error:", e);
      }
    }, 200);
  });

  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = "none";
    }
  });
}

// ==========================================
// Page 1: Trang chủ / Tủ lạnh (index.html)
// ==========================================

async function initPantryPage() {
  setupAutocomplete("ingredient-search", "ingredient-dropdown", "ingredient-id");

  const form = document.getElementById("add-lot-form");
  const refreshBtn = document.getElementById("btn-refresh-pantry");

  async function loadAndRender() {
    const lots = await getPantryLots();
    const container = document.getElementById("pantry-container");
    const totalEl = document.getElementById("stock-total");
    const captionEl = document.getElementById("stock-caption");
    const barFill = document.getElementById("stock-bar-fill");

    if (!container) return;
    container.innerHTML = "";

    if (!lots.length) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "empty-state";
      emptyDiv.style.textAlign = "center";
      emptyDiv.style.padding = "var(--space-6) var(--space-4)";
      emptyDiv.innerHTML = `
        <svg class="ico" width="48" height="48" style="opacity: 0.3; margin-bottom: var(--space-2);" aria-hidden="true"><use href="/static/icons.svg#i-dish-man"></use></svg>
        <h3 style="margin: 0 0 var(--space-1) 0;">Tủ lạnh đang trống</h3>
        <p style="color: var(--text-muted); font-size: var(--text-sm); margin: 0;">Thêm thực phẩm bạn vừa mua về ở biểu mẫu bên trái để EasyMeals gợi ý thực đơn!</p>
      `;
      container.appendChild(emptyDiv);
      if (totalEl) totalEl.textContent = "0 nguyên liệu";
      if (captionEl) captionEl.textContent = "Chưa có thực phẩm nào trong tủ.";
      if (barFill) barFill.style.width = "0%";
      return;
    }

    if (totalEl) totalEl.textContent = `${lots.length} nguyên liệu`;
    let totalQty = 0;
    lots.forEach((lot) => {
      totalQty += parseFloat(lot.remaining_quantity || 0);
    });
    if (captionEl) captionEl.textContent = `Tổng ${formatQty(totalQty)} đơn vị nguyên liệu còn lại trong tủ.`;
    const pct = Math.min(100, Math.round((totalQty / 5000) * 100));
    if (barFill) {
      barFill.style.width = `${pct}%`;
      barFill.classList.toggle("low", pct < 20);
    }

    const grid = document.createElement("div");
    grid.style.display = "grid";
    grid.style.gap = "var(--space-2)";

    lots.forEach((lot) => {
      const card = document.createElement("div");
      card.className = "pantry-item";
      card.style.display = "flex";
      card.style.justifyContent = "space-between";
      card.style.alignItems = "center";
      card.style.padding = "var(--space-2) var(--space-3)";
      card.style.border = "1px solid var(--border)";
      card.style.borderRadius = "var(--radius-sm)";
      card.style.background = "var(--surface)";

      const info = document.createElement("div");
      const name = document.createElement("div");
      name.style.fontWeight = "600";
      name.textContent = lot.ingredient_name || "Nguyên liệu";

      const sub = document.createElement("div");
      sub.style.fontSize = "var(--text-xs)";
      sub.style.color = "var(--text-muted)";
      let subText = `Còn: ${formatQty(lot.remaining_quantity)} ${lot.unit}`;
      sub.textContent = subText;
      if (lot.expires_at) {
        const expStatus = formatExpiryStatus(lot.expires_at);
        const expSpan = document.createElement("span");
        expSpan.style.marginLeft = "6px";
        if (expStatus && expStatus.isWarning) {
          expSpan.style.color = "var(--danger)";
          expSpan.style.fontWeight = "bold";
          expSpan.textContent = `• HSD: ${expStatus.text}`;
        } else if (expStatus) {
          expSpan.textContent = `• HSD: ${expStatus.text}`;
        } else {
          expSpan.textContent = `• HSD: ${formatDateVN(lot.expires_at)}`;
        }
        sub.appendChild(expSpan);
      }

      info.appendChild(name);
      info.appendChild(sub);

      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "var(--space-1)";
      actions.style.alignItems = "center";

      if (lot.expires_at) {
        const extBtn = document.createElement("button");
        extBtn.type = "button";
        extBtn.className = "btn btn-outline btn-sm";
        extBtn.style.fontSize = "var(--text-xs)";
        extBtn.style.padding = "2px 8px";
        extBtn.textContent = "+3 ngày";
        extBtn.title = "Gia hạn thêm 3 ngày khi sơ chế / bảo quản lại";
        extBtn.setAttribute("aria-label", `Gia hạn thêm 3 ngày cho ${lot.ingredient_name || "nguyên liệu"}`);
        extBtn.addEventListener("click", async () => {
          const d = new Date(lot.expires_at);
          d.setDate(d.getDate() + 3);
          lot.expires_at = d.toISOString().slice(0, 10);
          await updatePantryLot(lot);
          showToast(`Đã gia hạn +3 ngày cho ${lot.ingredient_name}`, "success");
          loadAndRender();
        });
        actions.appendChild(extBtn);
      }

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn btn-outline btn-sm";
      delBtn.style.color = "var(--danger)";
      delBtn.textContent = "Xoá";
      delBtn.setAttribute("aria-label", `Xoá ${lot.ingredient_name || "nguyên liệu"} khỏi tủ lạnh`);
      delBtn.addEventListener("click", async () => {
        if (confirm(`Xoá '${lot.ingredient_name}' khỏi tủ lạnh?`)) {
          await deletePantryLot(lot.id);
          showToast(`Đã xoá ${lot.ingredient_name}`, "info");
          loadAndRender();
        }
      });
      actions.appendChild(delBtn);

      card.appendChild(info);
      card.appendChild(actions);
      grid.appendChild(card);
    });

    container.appendChild(grid);

    // Also load movements
    loadMovements();
  }

  async function loadMovements() {
    const movContainer = document.getElementById("movements-container");
    if (!movContainer) return;
    const movements = await getStockMovements();
    movContainer.innerHTML = "";

    if (!movements.length) {
      const p = document.createElement("p");
      p.style.color = "var(--text-muted)";
      p.style.fontSize = "var(--text-sm)";
      p.textContent = "Chưa có biến động kho nào được ghi nhận.";
      movContainer.appendChild(p);
      return;
    }

    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "var(--space-1)";
    list.style.fontSize = "var(--text-xs)";

    movements.slice(0, 15).forEach((m) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.style.padding = "var(--space-1) 0";
      row.style.borderBottom = "1px solid var(--border)";

      const reasonLabel =
        m.reason === "meal_consumption"
          ? "Nấu ăn (-)"
          : m.reason === "correction"
          ? "Hoàn tác (+)"
          : "Mua vào (+)";

      const left = document.createElement("span");
      left.textContent = `${reasonLabel}: ${m.quantity_delta} (Lot: ${m.pantry_lot_id.slice(0, 8)}...)`;
      const time = document.createElement("span");
      time.style.color = "var(--text-muted)";
      time.textContent = new Date(m.created_at).toLocaleTimeString("vi-VN");

      row.appendChild(left);
      row.appendChild(time);
      list.appendChild(row);
    });

    movContainer.appendChild(list);
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ingId = document.getElementById("ingredient-id").value;
      const ingName = document.getElementById("ingredient-search").value.trim();
      const qty = document.getElementById("lot-quantity").value;
      const unit = document.getElementById("lot-unit").value;
      const exp = document.getElementById("lot-expiry").value || null;

      if (!ingId) {
        showToast("Vui lòng chọn một nguyên liệu từ danh sách gợi ý.", "warning");
        return;
      }

      try {
        await addPantryLot({
          ingredient_id: ingId,
          ingredient_name: ingName,
          quantity: qty,
          unit,
          expires_at: exp,
        });
        showToast(`Đã thêm ${ingName} vào tủ!`, "success");
        form.reset();
        document.getElementById("ingredient-id").value = "";
        loadAndRender();
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      }
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadAndRender);
  }

  loadAndRender();
}

// ==========================================
// Page 2: Thực đơn (planner.html)
// ==========================================

async function initPlannerPage() {
  const startInput = document.getElementById("plan-start");
  const endInput = document.getElementById("plan-end");
  const planForm = document.getElementById("generate-plan-form");
  const container = document.getElementById("plans-container");
  const alertBox = document.getElementById("shopping-alert");

  // Set default dates & day selector
  const daysSelector = document.getElementById("days-selector");
  const planDaysInput = document.getElementById("plan-days");

  if (startInput && !startInput.value) {
    startInput.value = new Date().toISOString().split("T")[0];
  }

  const updatePlanDates = (days) => {
    if (planDaysInput) planDaysInput.value = days;
    const s = startInput ? startInput.value : "";
    if (s && endInput) {
      const d = new Date(s);
      d.setDate(d.getDate() + parseInt(days) - 1);
      endInput.value = d.toISOString().split("T")[0];
    }
    const submitBtn = planForm?.querySelector("button[type='submit']");
    if (submitBtn) {
      submitBtn.textContent = `Lên thực đơn ${days} ngày`;
    }
  };

  if (daysSelector && planDaysInput) {
    daysSelector.querySelectorAll(".day-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        daysSelector.querySelectorAll(".day-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        const days = parseInt(chip.getAttribute("data-days"));
        localStorage.setItem("easymeals_selected_plan_days", days);
        updatePlanDates(days);
      });
    });

    const savedDays = parseInt(localStorage.getItem("easymeals_selected_plan_days") || PLAN_DEFAULT_DAYS);
    const initialDays = Math.max(PLAN_MIN_DAYS, Math.min(PLAN_MAX_DAYS, savedDays));
    const activeChip = daysSelector.querySelector(`[data-days="${initialDays}"]`);
    if (activeChip) {
      daysSelector.querySelectorAll(".day-chip").forEach((c) => c.classList.remove("active"));
      activeChip.classList.add("active");
    }
    updatePlanDates(initialDays);
  }

  if (startInput) {
    startInput.addEventListener("change", () => {
      const days = planDaysInput ? parseInt(planDaysInput.value) : PLAN_DEFAULT_DAYS;
      updatePlanDates(days);
    });
  }

  async function loadAndRenderPlans() {
    if (!container) return;
    const plans = await getMealPlans();
    container.innerHTML = "";

    if (!plans.length) {
      container.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: var(--space-8) var(--space-4);">
          <svg class="ico" width="48" height="48" style="opacity: 0.3; margin-bottom: var(--space-2);" aria-hidden="true"><use href="/static/icons.svg#i-calendar"></use></svg>
          <h3 style="margin: 0 0 var(--space-1) 0;">Chưa có thực đơn nào</h3>
          <p style="color: var(--text-muted); font-size: var(--text-sm); margin: 0;">Bấm nút "Tạo thực đơn mới" ở trên để EasyMeals tự động lên lịch bữa ăn phù hợp với thực phẩm trong tủ!</p>
        </div>
      `;
      if (alertBox) alertBox.style.display = "none";
      const freshnessAlert = document.getElementById("freshness-alert");
      if (freshnessAlert) freshnessAlert.style.display = "none";
      return;
    }

    // Cảnh báo tồn theo lô (A5 - Vòng 13): chỉ lô còn lượng; phân biệt
    // THIẾU HẾT HẠN (nhỏ hơn hôm nay, không thể dùng cho bữa nào trong chu kỳ)
    // và SẮP HẾT HẠN (còn dùng được, nêu ngày cuối cùng có thể dùng).
    // Ngưỡng theo từng lô (ngày hết hạn của chính nó), không lấy ngày cuối kế hoạch
    // làm đại diện cho mọi nguyên liệu như trước.
    const freshnessAlert = document.getElementById("freshness-alert");
    const freshnessAlertText = document.getElementById("freshness-alert-text");
    if (freshnessAlert && freshnessAlertText && plans.length > 0) {
      const lots = await getPantryLots();
      const lastPlan = plans[plans.length - 1];
      const lastDate = lastPlan.planned_for;
      const todayStr = new Date().toISOString().slice(0, 10);
      const toNum = (v) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : 0;
      };
      const activeLots = lots.filter(
        (l) => l.expires_at && l.expires_at <= lastDate && toNum(l.remaining_quantity) > 0
      );
      const expired = activeLots.filter((l) => l.expires_at < todayStr);
      const expiring = activeLots.filter((l) => l.expires_at >= todayStr);
      if (activeLots.length > 0) {
        // Ngày cuối cùng có thể dùng nguyên liệu = ngày hết hạn của chính lô đó
        // (ngày sớm nhất giữa các lô còn dùng được của nguyên liệu).
        const lines = [];
        if (expired.length) {
          lines.push(
            "Đã quá hạn, loại khỏi thực đơn hoặc kiểm tra rồi bỏ: " +
              expired
                .map((l) => `${l.ingredient_name} (hết hạn ${formatDateVN(l.expires_at)})`)
                .join(", ") +
              "."
        );
        }
        if (expiring.length) {
          const perIngr = {};
          for (const l of expiring) {
            if (!perIngr[l.ingredient_name] || l.expires_at < perIngr[l.ingredient_name]) {
              perIngr[l.ingredient_name] = l.expires_at;
            }
          }
          lines.push(
            "Sắp hết hạn trong chu kỳ thực đơn, cần dùng trước: " +
              Object.entries(perIngr)
                .map(([name, exp]) => `${name} (dùng trước ngày ${formatDateVN(exp)})`)
                .join(", ") +
              "."
          );
        }
        if (lines.length) {
          freshnessAlertText.textContent = lines.join("\n");
          freshnessAlertText.style.whiteSpace = "pre-line";
          freshnessAlert.style.display = "flex";
        } else {
          freshnessAlert.style.display = "none";
        }
      } else {
        freshnessAlert.style.display = "none";
      }
    }

    // Render grouped by planned_for date
    const grouped = {};
    plans.forEach((plan) => {
      const d = plan.planned_for;
      if (!grouped[d]) grouped[d] = [];
      grouped[d].push(plan);
    });

    const dates = Object.keys(grouped).sort();

    dates.forEach((d) => {
      const daySection = document.createElement("div");
      daySection.className = "day-plan-card card";
      daySection.style.marginBottom = "var(--space-4)";

      const dayHeader = document.createElement("div");
      dayHeader.style.display = "flex";
      dayHeader.style.justifyContent = "space-between";
      dayHeader.style.alignItems = "center";
      dayHeader.style.marginBottom = "var(--space-3)";
      dayHeader.style.borderBottom = "1px solid var(--border)";
      dayHeader.style.paddingBottom = "var(--space-2)";

      const dayTitle = document.createElement("h2");
      dayTitle.style.fontSize = "var(--text-base)";
      dayTitle.style.margin = "0";
      dayTitle.textContent = formatRelativeDate(d);

      dayHeader.appendChild(dayTitle);
      daySection.appendChild(dayHeader);

      const mealsRow = document.createElement("div");
      mealsRow.style.display = "grid";
      mealsRow.style.gap = "var(--space-3)";

      grouped[d].forEach((meal) => {
        const mealCard = document.createElement("div");
        mealCard.className = "meal-box";
        mealCard.style.padding = "var(--space-3)";
        mealCard.style.borderRadius = "var(--radius-sm)";
        mealCard.style.border = "1px solid var(--border)";
        mealCard.style.background = meal.eaten_at ? "var(--surface-variant)" : "var(--surface)";

        const mHeader = document.createElement("div");
        mHeader.style.display = "flex";
        mHeader.style.justifyContent = "space-between";
        mHeader.style.alignItems = "center";
        mHeader.style.marginBottom = "var(--space-2)";

        const mTitle = document.createElement("h3");
        mTitle.style.margin = "0";
        mTitle.style.fontSize = "var(--text-sm)";
        mTitle.textContent = PERIOD_LABELS[meal.meal_period] || meal.meal_period;

        const statusBadge = document.createElement("span");
        if (meal.eaten_at) {
          statusBadge.className = "badge";
          statusBadge.style.background = "var(--primary-subtle)";
          statusBadge.style.color = "var(--primary)";
          statusBadge.textContent = "Đã nấu ăn";
        } else {
          statusBadge.className = "badge";
          statusBadge.textContent = "Chưa ăn";
        }

        mHeader.appendChild(mTitle);
        mHeader.appendChild(statusBadge);
        mealCard.appendChild(mHeader);
        if ((meal.warnings || []).some((warning) => warning.reason === "avoided_ingredients")) {
          const warning = document.createElement("p");
          warning.className = "text-warning";
          warning.setAttribute("role", "status");
          warning.textContent = "Không đủ món phù hợp với nguyên liệu bạn tránh cho bữa này.";
          mealCard.appendChild(warning);
        }

        // Dishes
        const dishList = document.createElement("div");
        dishList.style.display = "flex";
        dishList.style.flexDirection = "column";
        dishList.style.gap = "var(--space-1)";
        dishList.style.marginBottom = "var(--space-3)";

        (meal.dishes || []).forEach((dish) => {
          const item = document.createElement("div");
          item.style.display = "flex";
          item.style.justifyContent = "space-between";
          item.style.alignItems = "center";
          item.style.fontSize = "var(--text-sm)";
          item.style.gap = "var(--space-2)";

          const left = document.createElement("div");
          left.style.display = "flex";
          left.style.alignItems = "center";
          left.style.gap = "var(--space-2)";
          left.style.flex = "1";

          const dName = document.createElement("span");
          dName.textContent = dish.recipe_name || "Món ăn";
          // Nhãn "Ăn lại" vẽ một lần duy nhất theo is_leftover; tên món trong
          // dữ liệu không chứa hậu tố "(Ăn lại)" (sửa lỗi hiện "… (Ăn lại) (Ăn lại)").
          if (dish.is_leftover && !/\(Ăn lại\)$/.test(dName.textContent)) {
            dName.textContent += " (Ăn lại)";
            dName.style.color = "var(--text-muted)";
          }
          left.appendChild(dName);
          if (dish.selection_reason) {
            const reason = document.createElement("span");
            reason.style.color = "var(--text-muted)";
            reason.style.fontSize = "var(--text-xs)";
            reason.textContent = dish.selection_reason;
            left.appendChild(reason);
          }

          const catBadge = document.createElement("span");
          catBadge.className = `badge badge-${dish.category}`;
          catBadge.style.fontSize = "0.75rem";
          catBadge.textContent = CAT_LABELS[dish.category] || dish.category;
          left.appendChild(catBadge);

          const right = document.createElement("div");
          right.style.display = "flex";
          right.style.alignItems = "center";
          right.style.gap = "var(--space-2)";

          const viewBtn = document.createElement("button");
          viewBtn.type = "button";
          viewBtn.className = "btn btn-outline btn-xs";
          viewBtn.style.padding = "2px 8px";
          viewBtn.style.fontSize = "0.75rem";
          viewBtn.textContent = "Xem";
          viewBtn.setAttribute("aria-label", `Xem công thức ${dish.recipe_name}`);
          viewBtn.addEventListener("click", () => {
            openRecipeModal(dish.recipe_id, dish.servings || 4);
          });
          right.appendChild(viewBtn);

          // B1: Đổi món cụ thể và Bỏ món (khi bữa chưa ăn)
          if (!meal.eaten_at) {
            const swapBtn = document.createElement("button");
            swapBtn.type = "button";
            swapBtn.className = "btn btn-outline btn-xs btn-swap-dish";
            swapBtn.style.padding = "2px 8px";
            swapBtn.style.fontSize = "0.75rem";
            swapBtn.textContent = "Đổi";
            swapBtn.title = "Đổi món này sang món khác cùng nhóm";
            swapBtn.setAttribute("aria-label", `Đổi món ${dish.recipe_name}`);
            swapBtn.addEventListener("click", async () => {
              const catalogue = await getCachedCatalogue();
              if (!catalogue || !catalogue.recipes) return;
              const allPlans = await getMealPlans();
              const usedIds = new Set(
                allPlans.flatMap((p) => p.dishes || []).filter((d) => !d.is_leftover && d.id !== dish.id).map((d) => d.recipe_id)
              );
              const candidates = catalogue.recipes.filter(
                (r) => r.category === dish.category && !usedIds.has(r.id)
              );
              if (!candidates.length) {
                showToast("Không còn món nào khác cùng nhóm chưa nấu trong chu kỳ.", "info");
                return;
              }
              const choiceNames = candidates.map((r, idx) => `${idx + 1}. ${r.name}`).join("\n");
              const input = prompt(`Chọn món thay thế cho "${dish.recipe_name}":\n\n${choiceNames}\n\nNhập số thứ tự:`);
              const selectedIdx = parseInt(input, 10) - 1;
              if (isNaN(selectedIdx) || selectedIdx < 0 || selectedIdx >= candidates.length) return;
              const chosenRecipe = candidates[selectedIdx];
              const prefs = (await getLocalSetting("recipe_preferences_v1")) || {};
              const avoided = new Set(prefs.avoidedIngredientIds || []);
              const violation = (chosenRecipe.ingredients || []).find((item) => avoided.has(item.ingredient_id));
              if (violation) {
                const ingredientName = (catalogue.ingredients || []).find((item) => item.id === violation.ingredient_id)?.name || "nguyên liệu đã chọn";
                if (!confirm(`Món này chứa ${ingredientName} mà bạn đã đặt cần tránh. Vẫn thêm?`)) return;
              }

              try {
                const updatedMeal = engineSwapDishInMeal(meal, dish.id, chosenRecipe, allPlans);
                const updatedPlans = allPlans.map((p) => (p.id === meal.id ? updatedMeal : p));
                await saveMealPlans(updatedPlans);

                const currentLots = await getPantryLots();
                const newShopping = engineRecomputeShoppingList(updatedPlans, currentLots, catalogue.recipes);
                await replacePlanShoppingItems(newShopping);

                showToast(`Đã đổi sang món "${chosenRecipe.name}"!`, "success");
                loadAndRenderPlans();
              } catch (err) {
                showToast(`Lỗi: ${err.message}`, "danger");
              }
            });
            right.appendChild(swapBtn);

            if ((meal.dishes || []).length > 1) {
              const removeBtn = document.createElement("button");
              removeBtn.type = "button";
              removeBtn.className = "btn btn-outline btn-xs btn-remove-dish";
              removeBtn.style.padding = "2px 6px";
              removeBtn.style.fontSize = "0.75rem";
              removeBtn.textContent = "✕";
              removeBtn.title = "Bỏ món này khỏi bữa ăn";
              removeBtn.setAttribute("aria-label", `Bỏ món ${dish.recipe_name}`);
              removeBtn.addEventListener("click", async () => {
                if (!confirm(`Bạn có chắc muốn bỏ món "${dish.recipe_name}" khỏi bữa ăn này?`)) return;
                try {
                  const allPlans = await getMealPlans();
                  const updatedMeal = engineRemoveDishFromMeal(meal, dish.id);
                  const updatedPlans = allPlans.map((p) => (p.id === meal.id ? updatedMeal : p));
                  await saveMealPlans(updatedPlans);

                  const catalogue = await getCachedCatalogue();
                  const currentLots = await getPantryLots();
                  const newShopping = engineRecomputeShoppingList(updatedPlans, currentLots, catalogue?.recipes || []);
                  await replacePlanShoppingItems(newShopping);

                  showToast(`Đã bỏ món "${dish.recipe_name}"!`, "success");
                  loadAndRenderPlans();
                } catch (err) {
                  showToast(`Lỗi: ${err.message}`, "danger");
                }
              });
              right.appendChild(removeBtn);
            }
          }

          item.appendChild(left);
          item.appendChild(right);
          dishList.appendChild(item);
        });

        mealCard.appendChild(dishList);

        // C3: ghi chú thuộc từng bữa, lưu cục bộ trong IndexedDB.
        const notesLabel = document.createElement("label");
        notesLabel.textContent = "Ghi chú bữa ăn";
        const notesInput = document.createElement("textarea");
        notesInput.maxLength = 500;
        notesInput.rows = 2;
        notesInput.value = meal.notes || "";
        notesInput.setAttribute("aria-label", `Ghi chú ${PERIOD_LABELS[meal.meal_period] || meal.meal_period} ${formatRelativeDate(d)}`);
        notesInput.style.width = "100%";
        notesInput.style.marginBottom = "var(--space-2)";
        notesInput.disabled = Boolean(meal.eaten_at);
        notesLabel.appendChild(notesInput);
        mealCard.appendChild(notesLabel);
        if (!meal.eaten_at) {
          const saveNotes = document.createElement("button");
          saveNotes.type = "button";
          saveNotes.className = "btn btn-outline btn-sm";
          saveNotes.textContent = "Lưu ghi chú";
          saveNotes.addEventListener("click", async () => {
            const value = notesInput.value.trim();
            const allPlans = await getMealPlans();
            const updated = allPlans.map((p) => p.id === meal.id ? { ...p, notes: value || null } : p);
            try {
              await saveMealPlans(updated);
              meal.notes = value || null;
              showToast("Đã lưu ghi chú trên thiết bị này.", "success");
            } catch (err) {
              showToast(`Không lưu được ghi chú: ${err.message}`, "danger");
            }
          });
          mealCard.appendChild(saveNotes);
        }

        // Action Buttons
        const actionRow = document.createElement("div");
        actionRow.style.display = "flex";
        actionRow.style.gap = "var(--space-2)";

        if (!meal.eaten_at) {
          const eatBtn = document.createElement("button");
          eatBtn.type = "button";
          eatBtn.className = "btn btn-primary btn-sm";
          eatBtn.textContent = "Đánh dấu Đã ăn (Trừ kho)";

          // A7 - Vòng 13: multiplier khẩu phần bằng số học chính xác: chia BigInt
          // nguyên với SCALE 6 chữ số thập phân của engine.js, làm tròn nửa lên.
          // Không dùng phép chia số thực (7/3 -> "2.3333333333333335" sai lệch).
          function computeMealMultiplier(servings, baseServings) {
            const SCALE = 1000000n;
            const s = BigInt(servings || 1);
            const b = BigInt(baseServings || 1);
            const fixed = (s * SCALE + b / 2n) / b;
            const whole = fixed / SCALE;
            const frac = fixed % SCALE;
            if (frac === 0n) return String(whole);
            return `${whole}.${frac.toString().padStart(6, "0")}`;
          }

          async function doEat(allowPartial) {
            eatBtn.disabled = true;
            eatBtn.textContent = "Đang trừ kho...";

            // Chế độ Mobile đóng gói (bundled) hoặc ngoại tuyến: tính toán trừ kho tại chỗ
            if (CATALOGUE_SOURCE === "bundled" || !navigator.onLine) {
              try {
                const currentLots = await getPantryLots();
                const catalogue = await getCachedCatalogue();
                if (!catalogue || !catalogue.recipes) {
                  throw new Error("Chưa nạp danh mục món ăn.");
                }
                let updatedLots = currentLots.map((l) => ({ ...l }));
                let allMovements = [];

                for (const d of meal.dishes || []) {
                  if (d.is_leftover) continue;
                  const recipe = (catalogue.recipes || []).find((r) => r.id === d.recipe_id);
                  if (!recipe) {
                    throw new Error(`Không tìm thấy công thức "${d.recipe_name || d.recipe_id}" trong danh mục.`);
                  }
                  // A7 - Vòng 13: multiplier tính bằng số học chính xác (BigInt, làm
                  // tròn nửa lên tới SCALE 6 chữ số của engine.js) thay vì chia số thực
                  // (7/3 -> "2.3333333333333335" làm trừ kho lệch ~2mg mỗi lần ăn).
                  const mult = computeMealMultiplier(d.servings, recipe.servings);
                  if (allowPartial) {
                    const deduction = engineDeductRecipeStockAvailable(
                      updatedLots,
                      recipe,
                      meal.id,
                      `eat_${meal.id}_${d.recipe_id}_${Date.now()}`,
                      mult,
                      catalogue.conversions || []
                    );
                    const updatedMap = new Map(deduction.updatedLots.map((l) => [l.id, l]));
                    updatedLots = updatedLots.map((l) => updatedMap.get(l.id) || l);
                    allMovements = allMovements.concat(deduction.movements);
                  } else {
                    const deduction = engineDeductRecipeStockFifo(
                      updatedLots,
                      recipe,
                      meal.id,
                      `eat_${meal.id}_${d.recipe_id}_${Date.now()}`,
                      mult,
                      catalogue.conversions || []
                    );
                    const updatedMap = new Map(deduction.updatedLots.map((l) => [l.id, l]));
                    updatedLots = updatedLots.map((l) => updatedMap.get(l.id) || l);
                    allMovements = allMovements.concat(deduction.movements);
                  }
                }

                await executeEatMealAtomic(meal.id, updatedLots, allMovements);
                showToast("Đã ghi nhận bữa ăn và trừ kho thành công!", "success");
                loadAndRenderPlans();
                return;
              } catch (err) {
                if (err.deficits) {
                  const defList = Object.values(err.deficits).map((v) => ({
                    name: v.ingredientName || v.name,
                    missing: v.missingQuantity || v.missing,
                    unit: v.unit,
                  }));
                  showDeficitDialog(
                    defList,
                    () => doEat(true),
                    () => {
                      addDeficitsToShoppingList(defList);
                      showToast("Đã thêm nguyên liệu thiếu vào danh sách đi chợ!", "success");
                    }
                  );
                } else {
                  showToast(`Lỗi: ${err.message}`, "danger");
                }
                eatBtn.disabled = false;
                eatBtn.textContent = "Đánh dấu Đã ăn (Trừ kho)";
                return;
              }
            }

            try {
              const currentLots = await getPantryLots();
              const payload = {
                pantry: toApiPantryLots(currentLots),
                meal_plan_id: meal.id,
                dishes: (meal.dishes || []).map((d) => ({
                  recipe_id: d.recipe_id,
                  is_leftover: d.is_leftover,
                  ...(d.servings ? { servings: d.servings } : {}),
                })),
                idempotency_key: `eat_${meal.id}_${Date.now()}`,
                allow_partial: allowPartial,
              };

              const res = await fetch("/api/planner/eat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              });

              if (!res.ok) {
                const errData = await res.json();
                if (res.status === 422 && errData.detail && errData.detail.deficits) {
                  const defList = Object.values(errData.detail.deficits);
                  showDeficitDialog(
                    defList,
                    () => doEat(true),
                    () => {
                      addDeficitsToShoppingList(defList);
                      showToast("Đã thêm nguyên liệu thiếu vào danh sách đi chợ!", "success");
                    }
                  );
                  eatBtn.disabled = false;
                  eatBtn.textContent = "Đánh dấu Đã ăn (Trừ kho)";
                  return;
                }
                throw new Error(errData.detail?.message || errData.detail || "Không thể trừ kho.");
              }

              const eatResult = await res.json();
              await executeEatMealAtomic(
                meal.id,
                mergeLocalPrices(eatResult.pantry, currentLots),
                eatResult.movements
              );
              showToast("Đã ghi nhận bữa ăn và trừ kho thành công!", "success");
              loadAndRenderPlans();
            } catch (err) {
              showToast(`Lỗi: ${err.message}`, "danger");
              eatBtn.disabled = false;
              eatBtn.textContent = "Đánh dấu Đã ăn (Trừ kho)";
            }
          }

          eatBtn.addEventListener("click", () => doEat(false));
          actionRow.appendChild(eatBtn);

          // B1: Sinh lại 1 bữa đơn lẻ mà không ảnh hưởng các bữa khác
          const regenBtn = document.createElement("button");
          regenBtn.type = "button";
          regenBtn.className = "btn btn-outline btn-sm";
          regenBtn.textContent = "Sinh lại bữa này";
          regenBtn.title = "Chọn lại món cân bằng cho bữa này, không lặp món với các bữa khác";
          regenBtn.addEventListener("click", async () => {
            if (
              !confirm(
                "Bạn có muốn đổi lại các món cho bữa ăn này? (Các bữa khác trong thực đơn sẽ được giữ nguyên)."
              )
            ) {
              return;
            }
            regenBtn.disabled = true;
            regenBtn.textContent = "Đang sinh lại...";
            try {
              const currentLots = await getPantryLots();
              const catalogue = await getCachedCatalogue();
              const allPlans = await getMealPlans();
              const conversions = catalogue?.conversions || [];
              const rawIngredientNames = {};
              const ingredientCategories = {};
              for (const ing of catalogue?.ingredients || []) {
                rawIngredientNames[ing.id] = ing.name;
                ingredientCategories[ing.id] = ing.category || "khac";
              }

              const updatedMeal = engineRegenerateSingleMeal(
                meal.id,
                allPlans,
                catalogue.recipes,
                currentLots,
                {
                  conversions,
                  avoided_ingredient_ids: ((await getLocalSetting("recipe_preferences_v1")) || {}).avoidedIngredientIds || [],
                }
              );

              const updatedPlans = allPlans.map((p) =>
                p.id === meal.id ? updatedMeal : p
              );
              await saveMealPlans(updatedPlans);

              const newShopping = engineRecomputeShoppingList(
                updatedPlans,
                currentLots,
                catalogue.recipes,
                {
                  conversions,
                  rawIngredientNames,
                  ingredientCategories,
                }
              );
              await replacePlanShoppingItems(newShopping);

              showToast("Đã sinh lại bữa ăn và cập nhật danh sách đi chợ!", "success");
              loadAndRenderPlans();
            } catch (err) {
              showToast(`Không thể sinh lại: ${err.message}`, "danger");
              regenBtn.disabled = false;
              regenBtn.textContent = "Sinh lại bữa này";
            }
          });
          actionRow.appendChild(regenBtn);

          // B1: Chuyển ngày hoặc chuyển bữa (trưa/tối)
          const reschedBtn = document.createElement("button");
          reschedBtn.type = "button";
          reschedBtn.className = "btn btn-outline btn-sm btn-reschedule-meal";
          reschedBtn.textContent = "Chuyển bữa";
          reschedBtn.title = "Đổi ngày hoặc chuyển giữa trưa và tối";
          reschedBtn.addEventListener("click", async () => {
            const currentPeriod = meal.meal_period === "lunch" ? "Trưa" : "Tối";
            const newPeriod = meal.meal_period === "lunch" ? "dinner" : "lunch";
            const newPeriodName = newPeriod === "lunch" ? "Trưa" : "Tối";
            const datePrompt = prompt(
              `Chuyển bữa ăn (${currentPeriod} ${meal.planned_for}):\n\nNhập ngày mới (YYYY-MM-DD):`,
              meal.planned_for
            );
            if (datePrompt === null) return;
            const targetDate = datePrompt.trim() || meal.planned_for;
            const switchPeriod = confirm(`Bạn có muốn chuyển sang bữa ${newPeriodName} không? (Bấm OK để chuyển sang ${newPeriodName}, Huỷ để giữ bữa ${currentPeriod})`);
            const targetPeriod = switchPeriod ? newPeriod : meal.meal_period;

            try {
              const allPlans = await getMealPlans();
              const updatedMeal = engineRescheduleMeal(meal, targetDate, targetPeriod, allPlans);
              const updatedPlans = allPlans.map((p) => (p.id === meal.id ? updatedMeal : p));
              await saveMealPlans(updatedPlans);
              showToast("Đã chuyển ngày/bữa thành công!", "success");
              loadAndRenderPlans();
            } catch (err) {
              showToast(`Lỗi: ${err.message}`, "danger");
            }
          });
          actionRow.appendChild(reschedBtn);
        } else {
          const undoBtn = document.createElement("button");
          undoBtn.type = "button";
          undoBtn.className = "btn btn-outline btn-sm";
          undoBtn.textContent = "Hoàn tác bữa ăn";
          undoBtn.addEventListener("click", async () => {
            undoBtn.disabled = true;
            undoBtn.textContent = "Đang hoàn tác...";

            // Chế độ Mobile đóng gói (bundled) hoặc ngoại tuyến: hoàn tác tại chỗ
            if (CATALOGUE_SOURCE === "bundled" || !navigator.onLine) {
              try {
                const currentLots = await getPantryLots();
                const movements = await getStockMovements();
                const mealMovements = movements.filter((m) => m.meal_plan_id === meal.id);

                const undoResult = engineReverseStockMovements(
                  currentLots,
                  mealMovements,
                  meal.id
                );

                await executeUndoEatMealAtomic(meal.id, undoResult.restoredLots, undoResult.reversalMovements);
                showToast("Đã hoàn tác và phục hồi nguyên liệu!", "success");
                loadAndRenderPlans();
                return;
              } catch (err) {
                showToast(`Lỗi: ${err.message}`, "danger");
                undoBtn.disabled = false;
                undoBtn.textContent = "Hoàn tác bữa ăn";
                return;
              }
            }

            try {
              const currentLots = await getPantryLots();
              const movements = await getStockMovements();
              const mealMovements = movements.filter((m) => m.meal_plan_id === meal.id);

              const payload = {
                pantry: toApiPantryLots(currentLots),
                meal_plan_id: meal.id,
                movements: mealMovements,
              };

              const res = await fetch("/api/planner/undo-eat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              });

              if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Không thể hoàn tác.");
              }

              const undoResult = await res.json();
              await executeUndoEatMealAtomic(
                meal.id,
                mergeLocalPrices(undoResult.pantry, currentLots),
                undoResult.reversal_movements
              );
              showToast("Đã hoàn tác và phục hồi nguyên liệu!", "success");
              loadAndRenderPlans();
            } catch (err) {
              showToast(`Lỗi: ${err.message}`, "danger");
              undoBtn.disabled = false;
              undoBtn.textContent = "Hoàn tác bữa ăn";
            }
          });
          actionRow.appendChild(undoBtn);
        }

        mealCard.appendChild(actionRow);
        mealsRow.appendChild(mealCard);
      });

      daySection.appendChild(mealsRow);
      container.appendChild(daySection);
    });
  }

  // Tuỳ chọn đồ ăn dư: đọc trạng thái người dùng chọn, lưu lại để lần sau giữ nguyên.
  function readAndPersistLeftoverPreferences() {
    const cb = document.getElementById("allow-leftovers");
    const sel = document.getElementById("leftover-days");
    if (cb) {
      localStorage.setItem("easymeals_allow_leftovers", cb.checked ? "1" : "0");
    }
    if (sel && sel.value) {
      const days = parseInt(sel.value, 10);
      if (Number.isFinite(days) && days >= LEFTOVER_MIN_DAYS && days <= LEFTOVER_MAX_DAYS) {
        localStorage.setItem("easymeals_leftover_days", String(days));
      }
    }
    const savedAllow = localStorage.getItem("easymeals_allow_leftovers");
    const savedDays = parseInt(
      localStorage.getItem("easymeals_leftover_days") || String(LEFTOVER_DEFAULT_DAYS),
      10
    );
    const allowLeftovers = cb ? !!cb.checked : savedAllow !== "0";
    return {
      allowLeftovers,
      leftoverDays: Number.isFinite(savedDays) ? savedDays : LEFTOVER_DEFAULT_DAYS,
    };
  }

  // Trước khi mở trang lần đầu (không submit), khôi phục lựa chọn đã lưu.
  function restoreLeftoverPreferences() {
    const cb = document.getElementById("allow-leftovers");
    const sel = document.getElementById("leftover-days");
    const savedAllow = localStorage.getItem("easymeals_allow_leftovers");
    const savedDays = localStorage.getItem("easymeals_leftover_days");
    if (cb && savedAllow !== null) cb.checked = savedAllow === "1";
    if (sel && savedDays !== null) sel.value = savedDays;
  }
  restoreLeftoverPreferences();
  restoreHouseholdSettings();
  const savedAvoidPreferences = (await getLocalSetting("recipe_preferences_v1")) || {};
  const savedAvoidIds = Array.isArray(savedAvoidPreferences.avoidedIngredientIds) ? savedAvoidPreferences.avoidedIngredientIds : [];
  const avoidanceDisclaimer = document.getElementById("avoid-ingredients-disclaimer");
  const avoidanceWarning = document.getElementById("avoid-ingredients-warning");
  if (avoidanceDisclaimer) avoidanceDisclaimer.hidden = savedAvoidIds.length === 0;
  if (savedAvoidIds.length && avoidanceWarning) {
    const catalogue = await getCachedCatalogue();
    const validIds = new Set((catalogue?.ingredients || []).map((ingredient) => ingredient.id));
    const stale = savedAvoidIds.some((id) => !validIds.has(id));
    avoidanceWarning.hidden = !stale;
    avoidanceWarning.textContent = stale
      ? "Một số nguyên liệu đã chọn không còn trong danh mục; sẽ được bỏ qua cho đến khi dữ liệu trở lại." : "";
  }

  // C1 - Vòng 13: đọc cài đặt hộ gia đình cục bộ từ localStorage (không lưu lên server).
  // Trả về đối tượng khớp schema HouseholdSettingsInput; giá trị rỗng -> engine dùng mặc định.
  function readHouseholdSettings() {
    const size = parseInt(localStorage.getItem("easymeals_household_size") || "1", 10);
    const servings = parseInt(localStorage.getItem("easymeals_default_servings") || "2", 10);
    let periods = ["lunch", "dinner"];
    try {
      const p = JSON.parse(localStorage.getItem("easymeals_meal_periods") || "[]");
      if (Array.isArray(p) && p.length) periods = p.filter((x) => ["breakfast", "lunch", "dinner"].includes(x));
    } catch (_) {}
    let skipDates = [];
    try {
      const sd = JSON.parse(localStorage.getItem("easymeals_skip_dates") || "[]");
      if (Array.isArray(sd)) skipDates = sd.filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(x));
    } catch (_) {}
    const planDays = parseInt(localStorage.getItem("easymeals_plan_days") || String(PLAN_DEFAULT_DAYS), 10);
    return {
      household_size: Number.isFinite(size) && size >= 1 ? size : 1,
      default_servings: Number.isFinite(servings) && servings >= 1 ? servings : 2,
      meal_periods: periods.length ? periods : ["lunch", "dinner"],
      skip_dates: skipDates,
      plan_days: Number.isFinite(planDays) && planDays >= PLAN_MIN_DAYS && planDays <= PLAN_MAX_DAYS ? planDays : PLAN_DEFAULT_DAYS,
    };
  }

  // C1 - Vòng 13: ghi cài đặt hộ gia đình cục bộ vào localStorage để lần sau giữ nguyên.
  function persistHouseholdSettings({ household_size, default_servings, meal_periods, skip_dates, plan_days }) {
    if (household_size != null) localStorage.setItem("easymeals_household_size", String(household_size));
    if (default_servings != null) localStorage.setItem("easymeals_default_servings", String(default_servings));
    if (meal_periods != null) localStorage.setItem("easymeals_meal_periods", JSON.stringify(meal_periods));
    if (skip_dates != null) localStorage.setItem("easymeals_skip_dates", JSON.stringify(skip_dates));
    if (plan_days != null) localStorage.setItem("easymeals_plan_days", String(plan_days));
  }

  // C1 - Vòng 13: khôi phục cài đặt hộ gia đình đã lưu vào các ô nhập trên trang.
  function restoreHouseholdSettings() {
    const hs = readHouseholdSettings();
    const sizeInput = document.getElementById("household-size");
    const servingsInput = document.getElementById("default-servings");
    if (sizeInput) sizeInput.value = hs.household_size;
    if (servingsInput) servingsInput.value = hs.default_servings;
    hs.meal_periods.forEach((p) => {
      const cb = document.getElementById("meal-" + p.slice(0, 4));
      if (cb) cb.checked = true;
    });
    // Bỏ chọn các bữa không nằm trong danh sách đã lưu
    ["breakfast", "lunch", "dinner"].forEach((p) => {
      const cb = document.getElementById("meal-" + p.slice(0, 4));
      if (cb && !hs.meal_periods.includes(p)) cb.checked = false;
    });
    const skipInput = document.getElementById("skip-dates");
    if (skipInput && hs.skip_dates.length) skipInput.value = hs.skip_dates.join(", ");
  }

  // C1 - Vòng 13: đọc cài đặt hộ gia đình từ các ô nhập và lưu vào localStorage.
  function persistHouseholdSettingsFromDom() {
    const sizeInput = document.getElementById("household-size");
    const servingsInput = document.getElementById("default-servings");
    const periodInputs = ["breakfast", "lunch", "dinner"].map((p) => {
      const cb = document.getElementById("meal-" + p.slice(0, 4));
      return cb && cb.checked ? p : null;
    }).filter(Boolean);
    const skipInput = document.getElementById("skip-dates");
    const skipDates = skipInput
      ? skipInput.value.split(",").map((s) => s.trim()).filter((s) => /^\d{4}-\d{2}-\d{2}$/.test(s))
      : [];
    persistHouseholdSettings({
      household_size: sizeInput ? parseInt(sizeInput.value, 10) || 1 : 1,
      default_servings: servingsInput ? parseInt(servingsInput.value, 10) || 2 : 2,
      meal_periods: periodInputs.length ? periodInputs : ["lunch", "dinner"],
      skip_dates: skipDates,
      plan_days: document.getElementById("plan-days") ? parseInt(document.getElementById("plan-days").value, 10) || PLAN_DEFAULT_DAYS : PLAN_DEFAULT_DAYS,
    });
  }

  // Lưu đợt thực đơn mới an toàn (A2 - Vòng 13): idempotency theo mã đợt,
  // gộp giữ bữa đã ăn, xoá các bữa chưa ăn bị thay khỏi kho trước khi lưu.
  async function saveGeneratedPlansBatch(existingPlans, data, mergeMode) {
    if (!data.meals || !data.meals.length) return;
    const periodId = data.period_id || data.meals[0].period_id;
    if (periodId && existingPlans.some((p) => String(p.period_id) === String(periodId))) {
      showToast("Thực đơn của đợt này đã được lưu trước đó.", "info");
      return;
    }
    const merged = engineMergeNewPlansIntoExisting(existingPlans, data.meals, mergeMode);
    await saveMealPlans(merged);
    const keptIds = new Set(merged.map((p) => String(p.id)));
    const removedIds = existingPlans
      .map((p) => String(p.id))
      .filter((id) => !keptIds.has(id));
    if (removedIds.length) await deleteMealPlansByIds(removedIds);
  }

  if (planForm) {
    planForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const s = startInput.value;
      const end = endInput.value;
      const days = planDaysInput ? parseInt(planDaysInput.value) : PLAN_DEFAULT_DAYS;

      if (!s || !end) return;

      if (days < PLAN_MIN_DAYS || days > PLAN_MAX_DAYS) {
        showToast(`Số ngày phải từ ${PLAN_MIN_DAYS} đến ${PLAN_MAX_DAYS} ngày.`, "warning");
        return;
      }

      const leftoverPrefs = readAndPersistLeftoverPreferences();
      const avoidancePreferences = (await getLocalSetting("recipe_preferences_v1")) || {};
      const avoidedIngredientIds = Array.isArray(avoidancePreferences.avoidedIngredientIds)
        ? avoidancePreferences.avoidedIngredientIds : [];
      const avoidanceDisclaimer = document.getElementById("avoid-ingredients-disclaimer");
      const avoidanceWarning = document.getElementById("avoid-ingredients-warning");
      if (avoidanceDisclaimer) avoidanceDisclaimer.hidden = avoidedIngredientIds.length === 0;
      const presentIngredients = new Set(((await getCachedCatalogue())?.ingredients || []).map((item) => item.id));
      const staleAvoidedIds = avoidedIngredientIds.filter((id) => !presentIngredients.has(id));
      if (avoidanceWarning) {
        avoidanceWarning.hidden = staleAvoidedIds.length === 0;
        avoidanceWarning.textContent = staleAvoidedIds.length
          ? "Một số nguyên liệu đã chọn không còn trong danh mục; sẽ được bỏ qua cho đến khi dữ liệu trở lại." : "";
      }
      // C1 - Vòng 13: lưu cài đặt hộ gia đình trước khi tính toán.
      persistHouseholdSettingsFromDom();

      // A2: nếu tạo thực đơn trùng ngày với bữa CHƯA ăn -> hỏi người dùng giữ hay thay.
      // Bữa đã ăn luôn được giữ; bấm Huỷ thì không tạo gì cả.
      const existingPlans = await getMealPlans();
      const recentCutoff = new Date(`${s}T00:00:00Z`);
      recentCutoff.setUTCDate(recentCutoff.getUTCDate() - 7);
      const recentlyCookedRecipeIds = [...new Set(existingPlans
        .filter((p) => p.eaten_at && String(p.planned_for).slice(0, 10) >= recentCutoff.toISOString().slice(0, 10)
          && String(p.planned_for).slice(0, 10) < s)
        .flatMap((p) => (p.dishes || []).filter((d) => !d.is_leftover).map((d) => d.recipe_id)))];
      const uneatenOverlap = existingPlans.filter(
        (p) =>
          !p.eaten_at &&
          String(p.planned_for).slice(0, 10) >= s &&
          String(p.planned_for).slice(0, 10) <= end
      );
      let mergeMode = "replace";
      if (uneatenOverlap.length > 0) {
        const choice = await askPlanConflictChoice();
        if (!choice) {
          showToast("Đã giữ nguyên thực đơn cũ.", "info");
          return;
        }
        mergeMode = choice;
      }

      const submitBtn = planForm.querySelector("button[type='submit']");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Đang tính toán thực đơn...";
      }

      // Chế độ Mobile đóng gói (bundled) hoặc ngoại tuyến: tính toán thực đơn tại chỗ
      if (CATALOGUE_SOURCE === "bundled" || !navigator.onLine) {
        try {
          const lots = await getPantryLots();
          const catalogue = await getCachedCatalogue();
          if (!catalogue || !catalogue.recipes) {
            throw new Error("Chưa nạp danh mục món ăn.");
          }

          const data = engineGeneratePeriodPlan(s, end, catalogue.recipes, lots, {
            allowLeftovers: leftoverPrefs.allowLeftovers,
            leftoverDays: leftoverPrefs.leftoverDays,
            // C1 - Vòng 13: truyền cài đặt hộ gia đình cục bộ (mặc định 1 người, trưa+tối).
            household_settings: readHouseholdSettings(),
            recently_cooked_recipe_ids: recentlyCookedRecipeIds,
            avoided_ingredient_ids: avoidedIngredientIds.filter((id) => presentIngredients.has(id)),
            // A7 - Vòng 13: đường offline/bundled cũng phải nhận quy đổi (gạo -> cơm)
            // kèm tên nguyên liệu gốc, khớp đường API.
            conversions: catalogue.conversions || [],
            raw_ingredient_names: Object.fromEntries(
              (catalogue.ingredients || []).map((ing) => [ing.id, ing.name])
            ),
          });
          await saveGeneratedPlansBatch(existingPlans, data, mergeMode);

          // A3: cập nhật kho versioned - thay mục sinh tự, giữ mục người dùng tự thêm.
          const planItems = await replacePlanShoppingItems(
            data.shopping_list || [],
            [data.period_id, (data.meals || [])[0] && data.meals[0].period_id].filter(Boolean)
          );
          if (planItems.length) {
            if (alertBox) alertBox.style.display = "flex";
          } else {
            if (alertBox) alertBox.style.display = "none";
          }

          showToast(avoidedIngredientIds.length
            ? `Đã tạo thực đơn thành công! Đã loại ${data.excluded_recipe_count || 0} món theo nguyên liệu cần tránh.`
            : "Đã tạo thực đơn thành công!", "success");
          loadAndRenderPlans();
          return;
        } catch (err) {
          showToast(`Lỗi: ${err.message}`, "danger");
          return;
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Tạo thực đơn mới";
          }
        }
      }

      try {
        const lots = await getPantryLots();
        const payload = {
          pantry: toApiPantryLots(lots),
          start_date: s,
          days,
          options: {
            allow_leftovers: leftoverPrefs.allowLeftovers,
            leftover_days: leftoverPrefs.leftoverDays,
            // C1 - Vòng 13: truyền cài đặt hộ gia đình cục bộ (mặc định 1 người, trưa+tối).
            household_settings: readHouseholdSettings(),
            recently_cooked_recipe_ids: recentlyCookedRecipeIds,
            avoided_ingredient_ids: avoidedIngredientIds.filter((id) => presentIngredients.has(id)),
          },
        };

        const res = await fetch("/api/planner/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Không thể tạo thực đơn.");
        }

        const data = await res.json();
        await saveGeneratedPlansBatch(existingPlans, data, mergeMode);

        // A3: cập nhật kho versioned - thay mục sinh tự, giữ mục người dùng tự thêm.
        const planItems = await replacePlanShoppingItems(
          data.shopping_list || [],
          [data.period_id, (data.meals || [])[0] && data.meals[0].period_id].filter(Boolean)
        );
        if (planItems.length) {
          if (alertBox) alertBox.style.display = "flex";
        } else {
          if (alertBox) alertBox.style.display = "none";
        }

        showToast(avoidedIngredientIds.length
          ? `Đã tạo thực đơn thành công! Đã loại ${data.excluded_recipe_count || 0} món theo nguyên liệu cần tránh.`
          : "Đã tạo thực đơn thành công!", "success");
        loadAndRenderPlans();
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Tạo thực đơn mới";
        }
      }
    });
  }

  loadAndRenderPlans();
}

// ==========================================
// Page 3: Công thức (recipes.html)
// ==========================================

async function initRecipesPage() {
  const grid = document.getElementById("recipes-grid");
  const filterBtns = document.querySelectorAll(".filter-btn");
  const dietFilter = document.getElementById("recipe-diet-filter");
  const spiceFilter = document.getElementById("recipe-spice-filter");
  const avoidFilter = document.getElementById("recipe-avoid-ingredients");
  const preferredFilter = document.getElementById("recipe-preferred-ingredients");
  const searchInput = document.getElementById("recipe-search");
  const includeFilter = document.getElementById("recipe-include-ingredients");
  const excludeFilter = document.getElementById("recipe-exclude-ingredients");
  const searchStatus = document.getElementById("recipe-search-status");
  let activeCat = "";
  // Ephemeral UI state: never persisted.
  let metaFilter = { timeLimit: 0, difficulty: "" };
  const metaStatus = document.getElementById("recipe-metadata-status");
  const metaChips = document.querySelectorAll(".meta-chip");
  const preferenceKey = "recipe_preferences_v1";
  let preferences = (await getLocalSetting(preferenceKey)) || {};
  if (dietFilter) dietFilter.value = preferences.diet || "";
  if (spiceFilter) spiceFilter.value = preferences.maxSpice ?? "";

  const cachedAtStart = await getCachedCatalogue();
  let availableIngredients = cachedAtStart?.ingredients || [];
  if (!availableIngredients.length) {
    try {
      const response = await fetch("/api/ingredients");
      if (response.ok) availableIngredients = await response.json();
    } catch { /* Catalogue filters remain usable when offline cache exists. */ }
  }
  const staleAvoidNote = document.getElementById("recipe-stale-avoid-note");
  if (staleAvoidNote) {
    const availableIds = new Set(availableIngredients.map((ingredient) => ingredient.id));
    staleAvoidNote.hidden = !(preferences.avoidedIngredientIds || []).some((id) => !availableIds.has(id));
  }
  if (avoidFilter || preferredFilter || includeFilter || excludeFilter) {
    availableIngredients.slice().sort((a, b) => a.name.localeCompare(b.name, "vi")).forEach((ingredient) => {
      [
        [avoidFilter, preferences.avoidedIngredientIds || []],
        [preferredFilter, preferences.preferredIngredientIds || []],
      ].forEach(([select, selectedIds]) => {
        if (!select) return;
        const option = document.createElement("option");
        option.value = ingredient.id;
        option.textContent = ingredient.name;
        option.selected = selectedIds.includes(ingredient.id);
        select.appendChild(option);
      });
      [includeFilter, excludeFilter].forEach((select) => {
        if (!select) return;
        const option = document.createElement("option");
        option.value = ingredient.id;
        option.textContent = ingredient.name;
        select.appendChild(option);
      });
    });
  }

  async function savePreferences() {
    preferences = {
      diet: dietFilter?.value || "",
      maxSpice: spiceFilter?.value || "",
      avoidedIngredientIds: avoidFilter ? Array.from(avoidFilter.selectedOptions, (option) => option.value) : [],
      preferredIngredientIds: preferredFilter ? Array.from(preferredFilter.selectedOptions, (option) => option.value) : [],
    };
    await setLocalSetting(preferenceKey, preferences);
  }

  async function loadAndRender() {
    if (!grid) return;
    grid.innerHTML = "";

    try {
      let recipes = [];
      const cached = await getCachedCatalogue();
      if (cached && cached.recipes) {
        recipes = cached.recipes;
      }

      if (!recipes.length) {
        const res = await fetch("/api/recipes");
        if (res.ok) recipes = await res.json();
      }

      const includedIds = Array.from(includeFilter?.selectedOptions || [], (option) => option.value);
      const excludedIds = Array.from(excludeFilter?.selectedOptions || [], (option) => option.value);
      recipes = filterRecipesForBrowse(filterRecipesByPreferences(recipes, preferences, activeCat), {
        query: searchInput?.value || "", includeIngredientIds: includedIds, excludeIngredientIds: excludedIds,
      });
      const metaResult = filterByMetadata(recipes, metaFilter);
      recipes = metaResult.recipes;
      if (metaStatus) {
        const msg = hiddenUnknownMessage(metaResult.hiddenUnknown, metaFilter);
        metaStatus.textContent = msg;
        metaStatus.hidden = !msg;
      }
      if (searchStatus) searchStatus.textContent = `${recipes.length} công thức phù hợp`;

      if (!recipes.length) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: var(--space-6);">
            <p style="color: var(--text-muted);">Không tìm thấy công thức phù hợp. Thử đổi từ khóa hoặc bộ lọc.</p>
          </div>
        `;
        return;
      }

      recipes.forEach((r) => {
        const card = document.createElement("div");
        card.className = "card recipe-card";
        card.style.cursor = "pointer";
        card.style.display = "flex";
        card.style.flexDirection = "column";
        card.style.justifyContent = "space-between";

        const top = document.createElement("div");
        const titleRow = document.createElement("div");
        titleRow.style.display = "flex";
        titleRow.style.justifyContent = "space-between";
        titleRow.style.alignItems = "flex-start";
        titleRow.style.marginBottom = "var(--space-2)";

        const h2 = document.createElement("h2");
        h2.style.fontSize = "var(--text-base)";
        h2.style.margin = "0";
        h2.textContent = r.name;

        const badge = document.createElement("span");
        badge.className = `badge badge-${r.category}`;
        badge.textContent = CAT_LABELS[r.category] || r.category;

        titleRow.appendChild(h2);
        titleRow.appendChild(badge);
        top.appendChild(titleRow);

        const ingCount = document.createElement("p");
        ingCount.style.fontSize = "var(--text-xs)";
        ingCount.style.color = "var(--text-muted)";
        ingCount.style.margin = "0 0 var(--space-3) 0";
        ingCount.textContent = `${(r.ingredients || []).length} nguyên liệu • Khẩu phần: ${r.servings} người`;
        top.appendChild(ingCount);

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-outline btn-sm";
        btn.style.width = "100%";
        btn.textContent = "Xem công thức & cách nấu";

        card.appendChild(top);
        card.appendChild(btn);

        card.addEventListener("click", () => openRecipeModal(r.id));
        grid.appendChild(card);
      });

      const unknownCount = (cached?.recipes || []).filter((recipe) => recipe.dietary_status === "unknown" || !recipe.dietary_source_url || !recipe.dietary_verified_at).length;
      const note = document.getElementById("recipe-filter-note");
      if (note && !preferences.diet) note.textContent = `${unknownCount} món đang thiếu thông tin chế độ ăn đã xác minh; không thể kết luận món phù hợp với dị ứng.`;
    } catch (err) {
      grid.innerHTML = "";
      const p = document.createElement("p");
      p.style.color = "var(--danger)";
      p.textContent = `Lỗi: ${err.message}`;
      grid.appendChild(p);
    }
  }

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active", "btn-primary"));
      filterBtns.forEach((b) => b.classList.add("btn-outline"));
      btn.classList.add("active", "btn-primary");
      btn.classList.remove("btn-outline");
      activeCat = btn.getAttribute("data-cat") || "";
      loadAndRender();
    });
  });

  metaChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const kind = chip.getAttribute("data-meta");
      const value = chip.getAttribute("data-value") || "";
      if (kind === "time") metaFilter = { ...metaFilter, timeLimit: Number(value) || 0 };
      else metaFilter = { ...metaFilter, difficulty: value };
      metaChips.forEach((other) => {
        if (other.getAttribute("data-meta") !== kind) return;
        const on = other === chip;
        other.classList.toggle("active", on);
        other.classList.toggle("btn-primary", on);
        other.classList.toggle("btn-outline", !on);
        other.setAttribute("aria-pressed", String(on));
      });
      loadAndRender();
    });
  });

  [dietFilter, spiceFilter, avoidFilter, preferredFilter].filter(Boolean).forEach((control) => {
    control.addEventListener("change", async () => { await savePreferences(); await loadAndRender(); });
  });
  searchInput?.addEventListener("input", loadAndRender);
  [includeFilter, excludeFilter].filter(Boolean).forEach((control) => control.addEventListener("change", loadAndRender));

  loadAndRender();
}

// ==========================================
// Page 4: Cần mua (shopping.html)
// ==========================================

async function initShoppingPage() {
  const container = document.getElementById("shopping-list-container");
  const clearBtn = document.getElementById("btn-clear-bought");
  const addBtn = document.getElementById("btn-add-to-pantry");
  // A4: lượng thực mua/hạn dùng người dùng chỉnh trên từng mục (reset sau mỗi lượt mua).
  let actualQuantities = {};
  let expiryOverrides = {};
  let cachedCatalogueForExpiry = null;

  // B3 & B4: Nhãn nhóm quầy hàng & format tiền tệ
  const SHOPPING_CAT_LABELS = {
    thit: "Thịt",
    gia_cam: "Gia cầm",
    hai_san: "Hải sản",
    trung_sua: "Trứng & Sữa",
    rau_cu: "Rau củ",
    cu_qua: "Củ quả",
    gao_bot_mi: "Gạo, Bột & Mì",
    gia_vi: "Gia vị",
    nuoc_cham_dau: "Nước chấm & Dầu ăn",
    khac: "Khác / Đồ dùng",
  };

  function formatVND(amount) {
    const n = Number(amount);
    if (!Number.isFinite(n) || n === 0) return "0 đ";
    return new Intl.NumberFormat("vi-VN").format(n) + " đ";
  }

  // A3 & B3: danh sách đi chợ nằm trong kho versioned IndexedDB, nhóm theo quầy hàng.
  function renderList(items) {
    if (!container) return;
    container.innerHTML = "";

    // B4: Cập nhật thẻ ngân sách & chi tiêu thực tế từ giá người dùng nhập
    const budget = engineCalculateShoppingBudget(items);
    const bEst = document.getElementById("budget-estimated");
    const bSpent = document.getElementById("budget-spent");
    if (bEst) bEst.textContent = formatVND(budget.total_estimated_budget);
    if (bSpent) bSpent.textContent = formatVND(budget.total_spent);

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: var(--space-6);">
          <svg class="ico" width="48" height="48" style="opacity: 0.3; margin-bottom: var(--space-2);" aria-hidden="true"><use href="/static/icons.svg#i-cart"></use></svg>
          <h3 style="margin: 0 0 var(--space-1) 0;">Không có món nào cần mua</h3>
          <p style="color: var(--text-muted); font-size: var(--text-sm); margin: 0;">Tủ lạnh của bạn đã đủ nguyên liệu cho thực đơn hiện tại!</p>
        </div>
      `;
      return;
    }

    const grouped = engineGroupShoppingItemsByCategory(items);
    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "var(--space-4)";

    for (const [catKey, groupItems] of Object.entries(grouped)) {
      if (!groupItems.length) continue;

      const groupSection = document.createElement("div");
      groupSection.className = "shopping-category-group";

      const catHeader = document.createElement("div");
      catHeader.style.cssText =
        "font-weight: 700; font-size: var(--text-sm); color: var(--primary); margin-bottom: var(--space-2); display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 4px;";
      const catTitleSpan = document.createElement("span");
      catTitleSpan.textContent = `${SHOPPING_CAT_LABELS[catKey] || catKey} (${groupItems.length})`;
      catHeader.appendChild(catTitleSpan);
      groupSection.appendChild(catHeader);

      const itemsGrid = document.createElement("div");
      itemsGrid.style.display = "grid";
      itemsGrid.style.gap = "var(--space-2)";

      groupItems.forEach((item) => {
        const row = document.createElement("div");
        row.className = "shopping-item-row";
        row.style.display = "flex";
        row.style.alignItems = "center";
        row.style.gap = "var(--space-2)";
        row.style.padding = "var(--space-2) var(--space-3)";
        row.style.border = "1px solid var(--border)";
        row.style.borderRadius = "var(--radius-sm)";
        row.style.background = item.bought ? "var(--surface-variant)" : "var(--surface)";

        const check = document.createElement("input");
        check.type = "checkbox";
        check.checked = Boolean(item.bought);
        check.setAttribute("aria-label", `Đánh dấu đã mua ${item.ingredient_name}`);
        check.addEventListener("change", async () => {
          await toggleShoppingItemBought(item.id);
          item.bought = check.checked;
          renderList(items);
        });
        const checkWrap = document.createElement("label");
        checkWrap.className = "shopping-check";
        checkWrap.appendChild(check);

        const label = document.createElement("div");
        label.className = "shopping-item-label";
        const nameRow = document.createElement("div");
        nameRow.style.display = "flex";
        nameRow.style.alignItems = "center";
        nameRow.style.gap = "var(--space-2)";

        const name = document.createElement("span");
        name.style.fontWeight = "600";
        name.textContent = `${item.ingredient_name}: ${formatQty(item.needed_quantity)} ${item.unit}`;
        if (item.bought) name.style.textDecoration = "line-through";
        nameRow.appendChild(name);

        // B3: Sửa số lượng cần mua
        const editQtyBtn = document.createElement("button");
        editQtyBtn.type = "button";
        editQtyBtn.className = "btn btn-outline btn-xs btn-edit-qty";
        editQtyBtn.style.cssText = "font-size: 10px; padding: 1px 5px; margin-left: 4px; border-color: var(--border);";
        editQtyBtn.textContent = "Sửa lượng";
        editQtyBtn.title = "Chỉnh sửa số lượng cần mua";
        editQtyBtn.setAttribute("aria-label", `Sửa số lượng cần mua ${item.ingredient_name}`);
        editQtyBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const newQty = prompt(`Nhập số lượng cần mua mới cho "${item.ingredient_name}" (${item.unit}):`, item.needed_quantity);
          if (newQty === null) return;
          const parsed = parseFloat(newQty);
          if (isNaN(parsed) || parsed <= 0) {
            showToast("Số lượng không hợp lệ.", "warning");
            return;
          }
          await updateShoppingItem(item.id, { needed_quantity: String(parsed) });
          item.needed_quantity = String(parsed);
          loadAndRender();
        });
        nameRow.appendChild(editQtyBtn);

        if (item.source === "manual") {
          const manualBadge = document.createElement("span");
          manualBadge.className = "badge";
          manualBadge.style.fontSize = "10px";
          manualBadge.textContent = "Tự thêm";
          nameRow.appendChild(manualBadge);
        }

        const dishes = document.createElement("div");
        dishes.style.fontSize = "var(--text-xs)";
        dishes.style.color = "var(--text-muted)";
        dishes.textContent = item.dish_names && item.dish_names.length
          ? `Dành cho: ${item.dish_names.join(", ")}`
          : "Mục tự thêm ngoài kế hoạch";

        label.appendChild(nameRow);
        label.appendChild(dishes);

        // B4: Ô nhập giá người dùng thực tế
        const priceBox = document.createElement("div");
        priceBox.style.cssText = "display: flex; flex-direction: column; gap: 2px;";
        const priceInput = document.createElement("input");
        priceInput.type = "text";
        priceInput.inputMode = "numeric";
        priceInput.className = "shopping-price-input";
        priceInput.placeholder = "Giá (đ)";
        priceInput.value = item.price || "";
        priceInput.setAttribute("aria-label", `Giá tiền cho ${item.ingredient_name} (đồng)`);
        priceInput.style.cssText = "width: 85px; padding: 4px 6px; font-size: var(--text-xs); border: 1px solid var(--border); border-radius: var(--radius-sm);";
        priceInput.addEventListener("input", () => {
          priceInput.value = priceInput.value.replace(/[^0-9]/g, "");
        });
        priceInput.addEventListener("change", async () => {
          const val = priceInput.value.trim();
          item.price = val || null;
          await updateShoppingItem(item.id, { price: item.price });
          // Cập nhật lại ngân sách
          const b = engineCalculateShoppingBudget(items);
          if (bEst) bEst.textContent = formatVND(b.total_estimated_budget);
          if (bSpent) bSpent.textContent = formatVND(b.total_spent);
        });
        priceBox.appendChild(priceInput);

        row.appendChild(checkWrap);
        row.appendChild(label);
        row.appendChild(priceBox);

        // A4: khi đã tích "đã mua" cho phép nhập LƯỢNG THỰC MUA khác ước tính và hạn dùng.
        const actualQty = actualQuantities[item.id] ?? item.needed_quantity;
        const actualExp = expiryOverrides[item.id] ?? defaultExpiryDate(
          item.category || resolveIngredientCategory(cachedCatalogueForExpiry, item.ingredient_id)
        );
        if (item.bought) {
          const edit = document.createElement("div");
          edit.style.cssText =
            "display:flex;flex-direction:column;gap:4px;margin-right:var(--space-1);";

          const qtyLabel = document.createElement("label");
          qtyLabel.style.cssText = "font-size:10px;color:var(--text-muted);";
          qtyLabel.textContent = "Thực mua";
          const qtyInput = document.createElement("input");
          qtyInput.type = "number";
          qtyInput.min = "0";
          qtyInput.step = "any";
          qtyInput.value = actualQty;
          qtyInput.setAttribute("aria-label", `Số lượng thực mua ${item.ingredient_name} (${item.unit})`);
          qtyInput.style.cssText =
            "width:70px;padding:3px 4px;font-size:11px;border:1px solid var(--border);border-radius:var(--radius-sm);";
          qtyInput.addEventListener("input", () => {
            actualQuantities[item.id] = qtyInput.value;
          });
          qtyLabel.appendChild(qtyInput);

          const expLabel = document.createElement("label");
          expLabel.style.cssText = "font-size:10px;color:var(--text-muted);";
          expLabel.textContent = "Hạn dùng";
          const expInput = document.createElement("input");
          expInput.type = "date";
          expInput.value = actualExp;
          expInput.setAttribute("aria-label", `Hạn dùng của ${item.ingredient_name}`);
          expInput.style.cssText =
            "width:115px;padding:3px 4px;font-size:11px;border:1px solid var(--border);border-radius:var(--radius-sm);";
          expInput.addEventListener("input", () => {
            expiryOverrides[item.id] = expInput.value;
          });
          expLabel.appendChild(expInput);

          edit.appendChild(qtyLabel);
          edit.appendChild(expLabel);
          row.appendChild(edit);
        }

        // B3: Nút xoá từng món
        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "btn btn-outline btn-xs";
        deleteBtn.style.cssText = "color: var(--danger); border-color: var(--border); padding: 4px 6px;";
        deleteBtn.innerHTML = "✕";
        deleteBtn.title = "Xoá món này";
        deleteBtn.setAttribute("aria-label", `Xoá ${item.ingredient_name} khỏi danh sách đi chợ`);
        deleteBtn.addEventListener("click", async () => {
          await deleteShoppingItemsByIds([item.id]);
          const newItems = items.filter((it) => it.id !== item.id);
          renderList(newItems);
          showToast(`Đã xoá "${item.ingredient_name}".`, "info");
        });
        row.appendChild(deleteBtn);

        itemsGrid.appendChild(row);
      });

      groupSection.appendChild(itemsGrid);
      list.appendChild(groupSection);
    }

    container.appendChild(list);
  }

  async function loadAndRender() {
    const items = await getShoppingItems();
    if (!cachedCatalogueForExpiry) {
      try {
        cachedCatalogueForExpiry = await getCachedCatalogue();
      } catch (_) {
        cachedCatalogueForExpiry = null;
      }
    }
    renderList(items);
  }

  const mergeBtn = document.getElementById("btn-merge-shopping");
  if (mergeBtn) {
    mergeBtn.addEventListener("click", async () => {
      mergeBtn.disabled = true;
      try {
        await mergeShoppingItems();
        showToast("Đã gộp các món cùng nguyên liệu và cùng thứ nguyên!", "success");
        await loadAndRender();
      } catch (err) {
        showToast(`Lỗi gộp: ${err.message}`, "danger");
      } finally {
        mergeBtn.disabled = false;
      }
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      await clearBoughtShoppingItems();
      showToast("Đã xoá các món đã chọn.", "info");
      loadAndRender();
    });
  }

  if (addBtn) {
    addBtn.addEventListener("click", async () => {
      // A4: chống bấm lặp — khoá nút trong suốt quá trình mua vào tủ.
      const items = await getShoppingItems();
      const bought = items.filter((i) => i.bought);
      if (!bought.length) {
        showToast("Vui lòng tích chọn các món bạn đã mua trước.", "warning");
        return;
      }

      addBtn.disabled = true;
      try {
        const overrides = {};
        for (const item of bought) {
          const ov = {};
          const actual = Number(actualQuantities[item.id] ?? item.needed_quantity);
          if (Number.isFinite(actual) && actual !== Number(item.needed_quantity)) {
            ov.quantity = String(actual);
          }
          if (expiryOverrides[item.id]) {
            ov.expires_at = expiryOverrides[item.id];
          }
          if (Object.keys(ov).length) overrides[item.id] = ov;
        }
        await executeBoughtToPantryAtomic(bought, overrides, cachedCatalogueForExpiry);
        showToast(`Đã chuyển ${bought.length} món vào tủ lạnh!`, "success");
      } catch (err) {
        showToast(`Không thể mua vào tủ: ${err.message}`, "danger");
      } finally {
        addBtn.disabled = false;
        actualQuantities = {};
        expiryOverrides = {};
      }
      loadAndRender();
    });
  }

  // B3: Thêm món tự do ngoài kế hoạch
  const addCustomBtn = document.getElementById("btn-add-custom-item");
  const customModal = document.getElementById("custom-item-modal");
  const closeCustomBtn = document.getElementById("btn-close-custom-modal");
  const customForm = document.getElementById("custom-item-form");

  if (addCustomBtn && customModal) {
    addCustomBtn.addEventListener("click", () => {
      customModal.style.display = "flex";
      activateDialog(customModal, {
        onEscape: () => {
          customModal.style.display = "none";
          deactivateDialog(customModal);
        },
      });
      const nameInput = document.getElementById("custom-item-name");
      if (nameInput) nameInput.focus();
    });
  }
  if (closeCustomBtn && customModal) {
    closeCustomBtn.addEventListener("click", () => {
      customModal.style.display = "none";
      deactivateDialog(customModal);
    });
  }
  if (customForm) {
    customForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("custom-item-name").value.trim();
      const qty = document.getElementById("custom-item-qty").value;
      const unit = document.getElementById("custom-item-unit").value;
      const cat = document.getElementById("custom-item-cat").value;
      const price = document.getElementById("custom-item-price").value;

      if (!name) return;
      await addShoppingItem(
        {
          ingredient_name: name,
          needed_quantity: qty,
          unit,
          category: cat,
          price: price ? price : null,
        },
        { source: SHOPPING_SOURCE_MANUAL }
      );
      showToast(`Đã thêm "${name}" vào danh sách đi chợ!`, "success");
      customModal.style.display = "none";
      deactivateDialog(customModal);
      customForm.reset();
      await loadAndRender();
    });
  }

  loadAndRender();
}

// ==========================================
// Page 5: Cài đặt & Quản lý Dữ liệu (settings.html)
// ==========================================

async function initSettingsPage() {
  const netBadge = document.getElementById("network-status");
  const persistBadge = document.getElementById("storage-persist-status");
  const catVersionBadge = document.getElementById("catalogue-version-badge");
  const lastBackupBadge = document.getElementById("last-backup-badge");
  const syncBtn = document.getElementById("btn-sync-catalogue");
  const exportBtn = document.getElementById("btn-export-json");
  const importInput = document.getElementById("import-file-input");

  // Update status indicators
  function updateNetStatus() {
    if (!netBadge) return;
    if (navigator.onLine) {
      netBadge.textContent = "Trực tuyến (Online)";
      netBadge.style.color = "var(--primary)";
    } else {
      netBadge.textContent = "Ngoại tuyến (Offline)";
      netBadge.style.color = "var(--danger)";
    }
  }

  updateNetStatus();
  window.addEventListener("online", updateNetStatus);
  window.addEventListener("offline", updateNetStatus);

  // Persistence check
  if (persistBadge) {
    const persisted = await requestStoragePersistence();
    persistBadge.textContent = persisted ? "Đã bật (Bền vững)" : "Chưa kích hoạt";
    persistBadge.style.color = persisted ? "var(--primary)" : "var(--text-muted)";
  }

  // Catalogue version
  if (catVersionBadge) {
    const cached = await getCachedCatalogue();
    catVersionBadge.textContent = cached?.catalogue_version || "Chưa tải";
  }

  // Last backup badge
  async function refreshBackupBadge() {
    if (!lastBackupBadge) return;
    const db = await openDB();
    const req = db.transaction("settings", "readonly").objectStore("settings").get("last_backup_at");
    req.onsuccess = () => {
      const val = req.result?.value;
      if (val) {
        lastBackupBadge.textContent = new Date(val).toLocaleString("vi-VN");
      } else {
        lastBackupBadge.textContent = "Chưa có bản sao lưu nào";
      }
    };
  }
  refreshBackupBadge();

  // F1 - Lịch sử & thống kê (tính tại máy từ IndexedDB)
  async function renderHistory() {
    const container = document.getElementById("history-container");
    if (!container) return;

    let summary;
    try {
      summary = await getHistorySummary();
    } catch (err) {
      container.textContent = `Không đọc được lịch sử: ${err.message}`;
      return;
    }

    container.replaceChildren();

    const money = (value) => `${Number(value || 0).toLocaleString("vi-VN")} đ`;
    const stats = [
      ["Bữa đã nấu (30 ngày)", String(summary.cooked.in_window)],
      ["Tổng bữa đã nấu", String(summary.cooked.total)],
      ["Đồ dư dùng lại (30 ngày)", String(summary.leftovers.reused_dishes_in_window)],
      [
        "Chi tiêu đã nhập (30 ngày)",
        summary.spending.lots_with_price ? money(summary.spending.in_window) : "Chưa có dữ liệu",
      ],
    ];

    const grid = document.createElement("div");
    grid.className = "stats-grid";
    grid.style.marginBottom = "var(--space-4)";
    for (const [label, value] of stats) {
      const card = document.createElement("div");
      card.className = "stat-card";
      const labelEl = document.createElement("span");
      labelEl.className = "stat-label";
      labelEl.textContent = label;
      const valueEl = document.createElement("span");
      valueEl.className = "stat-value";
      valueEl.textContent = value;
      card.append(labelEl, valueEl);
      grid.appendChild(card);
    }
    container.appendChild(grid);

    const mealsTitle = document.createElement("h3");
    mealsTitle.style.cssText = "font-size: var(--text-sm); margin: 0 0 var(--space-2);";
    mealsTitle.textContent = "Bữa ăn gần đây";
    container.appendChild(mealsTitle);

    if (!summary.cooked.meals.length) {
      const empty = document.createElement("p");
      empty.className = "subtitle";
      empty.style.margin = "0";
      empty.textContent = "Chưa có bữa ăn nào được đánh dấu “Đã ăn”.";
      container.appendChild(empty);
    } else {
      const list = document.createElement("ul");
      list.style.cssText = "list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-1);";
      for (const meal of summary.cooked.meals.slice(0, 5)) {
        const item = document.createElement("li");
        item.style.cssText =
          "display: flex; justify-content: space-between; gap: var(--space-2); padding: var(--space-1) 0; border-bottom: 1px solid var(--line); font-size: var(--text-sm);";
        const left = document.createElement("span");
        const period =
          meal.meal_period === "breakfast" ? "Sáng" : meal.meal_period === "lunch" ? "Trưa" : meal.meal_period === "dinner" ? "Tối" : meal.meal_period;
        left.textContent = `${formatDateVN(meal.planned_for)} · ${period}: ${meal.dish_names.join(", ") || "Không rõ món"}${
          meal.leftover_reuse_count ? ` (+${meal.leftover_reuse_count} đồ dư)` : ""
        }`;
        const right = document.createElement("span");
        right.style.color = "var(--text-muted)";
        right.style.fontSize = "var(--text-xs)";
        right.textContent = new Date(meal.eaten_at).toLocaleDateString("vi-VN");
        item.append(left, right);
        list.appendChild(item);
      }
      container.appendChild(list);
    }

    if (summary.cooked.top_recipes.length) {
      const top = document.createElement("p");
      top.style.cssText = "font-size: var(--text-xs); color: var(--text-muted); margin: var(--space-3) 0 0;";
      top.textContent = `Nấu nhiều nhất (30 ngày): ${summary.cooked.top_recipes
        .map((r) => `${r.name} ×${r.count}`)
        .join(" · ")}`;
      container.appendChild(top);
    }

    const stock = document.createElement("p");
    stock.style.cssText = "font-size: var(--text-xs); color: var(--text-muted); margin: var(--space-2) 0 0;";
    stock.textContent = `Biến động kho (30 ngày): ${summary.stock.in_window} lần (${summary.stock.consumed_count} lần trừ, ${summary.stock.restored_count} lần cộng). Tổng cộng: ${summary.stock.total_movements} bản ghi.`;
    container.appendChild(stock);

    if (summary.spending.lots_missing_price > 0) {
      const spendNote = document.createElement("p");
      spendNote.style.cssText = "font-size: var(--text-xs); color: var(--text-muted); margin: var(--space-1) 0 0;";
      spendNote.textContent = `Chi tiêu chỉ tính ${summary.spending.lots_with_price} lô có nhập giá; ${summary.spending.lots_missing_price} lô chưa có giá nên không được tính.`;
      container.appendChild(spendNote);
    }

    if (summary.waste.expired_lot_count > 0) {
      const warn = document.createElement("p");
      warn.style.cssText = "font-size: var(--text-xs); color: var(--danger); margin: var(--space-2) 0 0;";
      warn.textContent = `${summary.waste.expired_lot_count} lô đã quá hạn mà vẫn còn trong tủ: ${summary.waste.expired_lots
        .slice(0, 5)
        .map((lot) => `${lot.ingredient_name || lot.ingredient_id} (${lot.remaining_quantity} ${lot.unit})`)
        .join(", ")}.`;
      container.appendChild(warn);
    }

    const wasteNote = document.createElement("p");
    wasteNote.style.cssText = "font-size: var(--text-xs); color: var(--text-muted); margin: var(--space-2) 0 0;";
    wasteNote.textContent =
      "Ứng dụng chưa có chức năng ghi nhận lãng phí; mục trên chỉ là đồ đã quá hạn còn trong tủ, không phải số liệu lãng phí đã xác nhận.";
    container.appendChild(wasteNote);
  }

  renderHistory();

  // Theme mode & Palette selection (F1)
  function updateThemeUI() {
    let savedTheme = "system";
    try {
      savedTheme = localStorage.getItem("theme") || "system";
    } catch (e) {}

    let savedPalette = "green";
    try {
      savedPalette = localStorage.getItem("palette") || "green";
    } catch (e) {}

    document.querySelectorAll(".theme-mode-btn").forEach((btn) => {
      const mode = btn.dataset.mode;
      if (mode === savedTheme) {
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-secondary");
      } else {
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-secondary");
      }
    });

    document.querySelectorAll(".palette-btn").forEach((btn) => {
      const pal = btn.dataset.palette;
      if (pal === savedPalette) {
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-secondary");
      } else {
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-secondary");
      }
    });
  }

  updateThemeUI();

  document.querySelectorAll(".theme-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.mode;
      try {
        localStorage.setItem("theme", mode);
      } catch (e) {}
      if (mode === "light" || mode === "dark") {
        document.documentElement.setAttribute("data-theme", mode);
      } else {
        document.documentElement.removeAttribute("data-theme");
      }
      updateThemeUI();
    });
  });

  document.querySelectorAll(".palette-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pal = btn.dataset.palette;
      try {
        localStorage.setItem("palette", pal);
      } catch (e) {}
      document.documentElement.setAttribute("data-palette", pal);
      updateThemeUI();
    });
  });

  // Sync catalogue
  if (syncBtn) {
    syncBtn.addEventListener("click", async () => {
      if (!navigator.onLine) {
        showToast("Không thể đồng bộ khi đang ngoại tuyến.", "warning");
        return;
      }
      syncBtn.disabled = true;
      syncBtn.textContent = "Đang đồng bộ...";
      try {
        const result = await syncCatalogue();
        showToast(
          result.updated ? "Đã cập nhật danh mục mới nhất!" : "Danh mục hiện tại đã là bản mới nhất.",
          "success"
        );
        if (catVersionBadge) {
          catVersionBadge.textContent = result.data.catalogue_version;
        }
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      } finally {
        syncBtn.disabled = false;
        syncBtn.textContent = "Đồng bộ danh mục mới nhất";
      }
    });
  }

  // Export JSON
  if (exportBtn) {
    exportBtn.addEventListener("click", async () => {
      try {
        const backup = await exportBackupJSON();
        const jsonStr = JSON.stringify(backup, null, 2);
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const dateStr = new Date().toISOString().split("T")[0];
        a.href = url;
        a.download = `easymeals-backup-${dateStr}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast("Đã tải về file sao lưu (.json) thành công!", "success");
        refreshBackupBadge();
      } catch (err) {
        showToast(`Lỗi xuất dữ liệu: ${err.message}`, "danger");
      }
    });
  }

  // Import JSON with Modal
  if (importInput) {
    importInput.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          // F3: nhận cả file sao lưu của ứng dụng di động (định dạng phẳng).
          const raw = normalizeBackupPayload(JSON.parse(event.target.result));
          validateBackupJSON(raw);

          // Show Import Modal
          const modal = document.getElementById("import-modal-overlay");
          const summary = document.getElementById("import-summary");
          const replaceBtn = document.getElementById("btn-confirm-replace");
          const mergeBtn = document.getElementById("btn-confirm-merge");
          const cancelBtn = document.getElementById("btn-cancel-import");

          if (!modal) return;
          const lotCount = raw.data.pantry.length;
          const planCount = raw.data.plans.length;
          const movementCount = raw.data.movements.length;
          const shoppingCount = (raw.data.shopping || []).length;
          const exportedAt = raw.exported_at ? new Date(raw.exported_at).toLocaleString("vi-VN") : "không rõ";
          summary.textContent =
            `File hợp lệ (schema ${raw.schema_version}, ứng dụng ${raw.app_version || "cũ"}). ` +
            `Chứa: ${lotCount} thực phẩm, ${planCount} bữa ăn, ${movementCount} biến động kho, ${shoppingCount} mục đi chợ. Ngày xuất: ${exportedAt}. ` +
            "Dữ liệu cũ hơn sẽ được nâng cấp tự động; không mất lô, bữa ăn hay biến động kho.";
          modal.style.display = "flex";

          const closeModal = () => {
            modal.style.display = "none";
            importInput.value = "";
            deactivateDialog(modal);
          };

          activateDialog(modal, { onEscape: closeModal });
          cancelBtn.onclick = closeModal;

          replaceBtn.onclick = async () => {
            if (confirm("Ghi đè sẽ xoá toàn bộ dữ liệu hiện tại trên máy này. Tiếp tục?")) {
              await importBackupJSON(raw, "replace");
              showToast("Đã ghi đè toàn bộ dữ liệu từ file thành công!", "success");
              closeModal();
              refreshBackupBadge();
              renderHistory();
            }
          };

          mergeBtn.onclick = async () => {
            await importBackupJSON(raw, "merge");
            showToast("Đã hợp nhất dữ liệu thành công!", "success");
            closeModal();
            refreshBackupBadge();
            renderHistory();
          };
        } catch (err) {
          showToast(`File không hợp lệ: ${err.message}`, "danger");
          importInput.value = "";
        }
      };
      reader.readAsText(file);
    });
  }

  // Clear all data (2-step confirmation)
  const clearBtn = document.getElementById("btn-clear-all-data");
  const clearModal = document.getElementById("clear-modal-overlay");
  const cancelClearBtn = document.getElementById("btn-cancel-clear");
  const confirmClearBtn = document.getElementById("btn-confirm-clear");

  if (clearBtn && clearModal) {
    const closeClearModal = () => {
      clearModal.style.display = "none";
      deactivateDialog(clearModal);
    };

    clearBtn.addEventListener("click", () => {
      clearModal.style.display = "flex";
      activateDialog(clearModal, { onEscape: closeClearModal });
    });

    if (cancelClearBtn) {
      cancelClearBtn.addEventListener("click", closeClearModal);
    }

    if (confirmClearBtn) {
      confirmClearBtn.addEventListener("click", async () => {
        await clearAllPersonalData();
        localStorage.removeItem("easymeals_shopping_list");
        showToast("Đã xoá sạch toàn bộ dữ liệu cá nhân trên máy!", "info");
        closeClearModal();
        refreshBackupBadge();
        renderHistory();
      });
    }
  }
}

// ==========================================
// Bootstrap Application
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  // 1. Register Service Worker (chỉ đăng ký cho Web PWA, bản mobile đóng gói không dùng SW mạng)
  if ("serviceWorker" in navigator && !window.location.protocol.startsWith("file") && CATALOGUE_SOURCE !== "bundled") {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.warn("ServiceWorker registration failed:", err);
    });
  }

  // Tự động đồng bộ / nạp danh mục đóng gói ngay khi khởi động
  syncCatalogue().catch((err) => console.warn("Initial sync catalogue:", err));

  // 2. Offline banner
  const banner = document.getElementById("offline-banner");
  function checkOnlineState() {
    if (banner) {
      banner.style.display = navigator.onLine ? "none" : "block";
    }
  }
  checkOnlineState();
  window.addEventListener("online", checkOnlineState);
  window.addEventListener("offline", checkOnlineState);

  // 3. Theme toggle
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const isDarkPreferred = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      const current = document.documentElement.getAttribute("data-theme") || (isDarkPreferred ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem("theme", next);
      } catch (e) {}
    });
  });

  // 4. Close modal on click outside
  const modalOverlay = document.getElementById("recipe-modal-overlay");
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeRecipeModal();
    });
  }

  // 5. Initialize page-specific controller
  if (document.getElementById("pantry-container")) {
    initPantryPage();
  }
  if (document.getElementById("plans-container")) {
    initPlannerPage();
  }
  if (document.getElementById("recipes-grid")) {
    initRecipesPage();
  }
  if (document.getElementById("shopping-list-container")) {
    initShoppingPage();
  }
  if (document.getElementById("btn-export-json")) {
    initSettingsPage();
  }
});
