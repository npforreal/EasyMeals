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
  addPantryLot,
  deletePantryLot,
  getMealPlans,
  saveMealPlans,
  executeEatMealAtomic,
  executeUndoEatMealAtomic,
  getStockMovements,
  getCachedCatalogue,
  syncCatalogue,
  exportBackupJSON,
  validateBackupJSON,
  importBackupJSON,
  CATALOGUE_SOURCE,
} from "./js/storage.js";
import {
  generatePeriodPlan as engineGeneratePeriodPlan,
  deductRecipeStockFifo as engineDeductRecipeStockFifo,
  deductRecipeStockAvailable as engineDeductRecipeStockAvailable,
  reverseStockMovements as engineReverseStockMovements,
  getTotalIngredientStock as engineGetTotalIngredientStock,
} from "./js/engine.js";
import {
  formatDateVN,
  formatRelativeDate,
  formatExpiryStatus,
} from "./js/formatters.js";

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
  const steps = recipe.instructions || [];

  let wakeLock = null;
  if ("wakeLock" in navigator) {
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

  const closeDlg = () => { dlgOverlay.style.display = "none"; };
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

export function addDeficitsToShoppingList(deficits) {
  let existing = [];
  try {
    const raw = localStorage.getItem("easymeals_shopping_list");
    if (raw) existing = JSON.parse(raw);
  } catch (_) {}
  for (const d of deficits) {
    existing.push({
      ingredient_id: d.ingredient_id || d.id || ("custom_" + Date.now()),
      ingredient_name: d.ingredient_name || d.name,
      needed_quantity: String(d.missing_quantity || d.missing || d.quantity || "200"),
      unit: d.unit || "g",
      dish_names: [],
    });
  }
  localStorage.setItem("easymeals_shopping_list", JSON.stringify(existing));
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
  if (modalOverlay) modalOverlay.style.display = "none";
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

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn btn-outline btn-sm";
      delBtn.style.color = "var(--danger)";
      delBtn.textContent = "Xoá";
      delBtn.addEventListener("click", async () => {
        if (confirm(`Xoá '${lot.ingredient_name}' khỏi tủ lạnh?`)) {
          await deletePantryLot(lot.id);
          showToast(`Đã xoá ${lot.ingredient_name}`, "info");
          loadAndRender();
        }
      });

      card.appendChild(info);
      card.appendChild(delBtn);
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

  // Set default dates: today -> +6 days (7 days total)
  if (startInput && endInput && !startInput.value) {
    const today = new Date();
    const nextWeek = new Date();
    nextWeek.setDate(today.getDate() + 6);
    startInput.value = today.toISOString().split("T")[0];
    endInput.value = nextWeek.toISOString().split("T")[0];
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
      return;
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
          if (dish.is_leftover) {
            dName.textContent += " (Ăn lại)";
            dName.style.color = "var(--text-muted)";
          }
          left.appendChild(dName);

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
          viewBtn.textContent = "Xem công thức";
          viewBtn.addEventListener("click", () => {
            openRecipeModal(dish.recipe_id, dish.servings || 4);
          });
          right.appendChild(viewBtn);

          item.appendChild(left);
          item.appendChild(right);
          dishList.appendChild(item);
        });

        mealCard.appendChild(dishList);

        // Action Buttons
        const actionRow = document.createElement("div");
        actionRow.style.display = "flex";
        actionRow.style.gap = "var(--space-2)";

        if (!meal.eaten_at) {
          const eatBtn = document.createElement("button");
          eatBtn.type = "button";
          eatBtn.className = "btn btn-primary btn-sm";
          eatBtn.textContent = "Đánh dấu Đã ăn (Trừ kho)";

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
                  const mult = d.servings ? String(d.servings / recipe.servings) : "1";
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
                pantry: currentLots,
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
              await executeEatMealAtomic(meal.id, eatResult.pantry, eatResult.movements);
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
                pantry: currentLots,
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
              await executeUndoEatMealAtomic(meal.id, undoResult.pantry, undoResult.reversal_movements);
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

  if (planForm) {
    planForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const s = startInput.value;
      const end = endInput.value;
      if (!s || !end) return;

      const startDate = new Date(s);
      const endDate = new Date(end);
      const days = Math.round((endDate - startDate) / (1000 * 3600 * 24)) + 1;

      if (days <= 0 || days > 31) {
        showToast("Số ngày phải từ 1 đến 31 ngày.", "warning");
        return;
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

          const data = engineGeneratePeriodPlan(s, end, catalogue.recipes, lots, { allowLeftovers: true });
          await saveMealPlans(data.meals);

          if (data.shopping_list && data.shopping_list.length) {
            localStorage.setItem("easymeals_shopping_list", JSON.stringify(data.shopping_list));
            if (alertBox) alertBox.style.display = "flex";
          } else {
            localStorage.removeItem("easymeals_shopping_list");
            if (alertBox) alertBox.style.display = "none";
          }

          showToast("Đã tạo thực đơn thành công!", "success");
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
          pantry: lots,
          start_date: s,
          days,
          options: { allow_leftovers: true },
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
        await saveMealPlans(data.meals);

        if (data.shopping_list && data.shopping_list.length) {
          localStorage.setItem("easymeals_shopping_list", JSON.stringify(data.shopping_list));
          if (alertBox) alertBox.style.display = "flex";
        } else {
          localStorage.removeItem("easymeals_shopping_list");
          if (alertBox) alertBox.style.display = "none";
        }

        showToast("Đã tạo thực đơn thành công!", "success");
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
  let activeCat = "";

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

      if (activeCat) {
        recipes = recipes.filter((r) => r.category === activeCat);
      }

      if (!recipes.length) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: var(--space-6);">
            <p style="color: var(--text-muted);">Không tìm thấy món ăn nào thuộc nhóm này.</p>
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

  loadAndRender();
}

// ==========================================
// Page 4: Cần mua (shopping.html)
// ==========================================

async function initShoppingPage() {
  const container = document.getElementById("shopping-list-container");
  const clearBtn = document.getElementById("btn-clear-bought");
  const addBtn = document.getElementById("btn-add-to-pantry");

  function getShoppingItems() {
    try {
      const raw = localStorage.getItem("easymeals_shopping_list");
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveShoppingItems(items) {
    localStorage.setItem("easymeals_shopping_list", JSON.stringify(items));
  }

  function renderList() {
    if (!container) return;
    const items = getShoppingItems();
    container.innerHTML = "";

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

    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "var(--space-2)";

    items.forEach((item, idx) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.gap = "var(--space-3)";
      row.style.padding = "var(--space-2) var(--space-3)";
      row.style.border = "1px solid var(--border)";
      row.style.borderRadius = "var(--radius-sm)";
      row.style.background = "var(--surface)";

      const check = document.createElement("input");
      check.type = "checkbox";
      check.checked = Boolean(item.bought);
      check.addEventListener("change", () => {
        item.bought = check.checked;
        saveShoppingItems(items);
      });

      const label = document.createElement("div");
      label.style.flex = "1";
      const name = document.createElement("div");
      name.style.fontWeight = "600";
      name.textContent = `${item.ingredient_name}: ${formatQty(item.needed_quantity)} ${item.unit}`;

      const dishes = document.createElement("div");
      dishes.style.fontSize = "var(--text-xs)";
      dishes.style.color = "var(--text-muted)";
      dishes.textContent = `Dành cho: ${(item.dish_names || []).join(", ") || "Các món đã lên lịch"}`;

      label.appendChild(name);
      label.appendChild(dishes);

      row.appendChild(check);
      row.appendChild(label);
      list.appendChild(row);
    });

    container.appendChild(list);
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      const items = getShoppingItems();
      const remaining = items.filter((i) => !i.bought);
      saveShoppingItems(remaining);
      showToast("Đã xoá các món đã chọn.", "info");
      renderList();
    });
  }

  if (addBtn) {
    addBtn.addEventListener("click", async () => {
      const items = getShoppingItems();
      const bought = items.filter((i) => i.bought);
      if (!bought.length) {
        showToast("Vui lòng tích chọn các món bạn đã mua trước.", "warning");
        return;
      }

      for (const item of bought) {
        await addPantryLot({
          ingredient_id: item.ingredient_id,
          ingredient_name: item.ingredient_name,
          quantity: item.needed_quantity,
          unit: item.unit,
        });
      }

      const remaining = items.filter((i) => !i.bought);
      saveShoppingItems(remaining);
      showToast(`Đã chuyển ${bought.length} món vào tủ lạnh!`, "success");
      renderList();
    });
  }

  renderList();
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
          const raw = JSON.parse(event.target.result);
          validateBackupJSON(raw);

          // Show Import Modal
          const modal = document.getElementById("import-modal-overlay");
          const summary = document.getElementById("import-summary");
          const replaceBtn = document.getElementById("btn-confirm-replace");
          const mergeBtn = document.getElementById("btn-confirm-merge");
          const cancelBtn = document.getElementById("btn-cancel-import");

          if (!modal) return;
          summary.textContent = `File hợp lệ! Chứa: ${raw.data.pantry.length} thực phẩm, ${raw.data.plans.length} bữa ăn đã lên lịch. Ngày xuất: ${new Date(raw.exported_at).toLocaleString("vi-VN")}.`;
          modal.style.display = "flex";

          const closeModal = () => {
            modal.style.display = "none";
            importInput.value = "";
          };

          cancelBtn.onclick = closeModal;

          replaceBtn.onclick = async () => {
            if (confirm("Ghi đè sẽ xoá toàn bộ dữ liệu hiện tại trên máy này. Tiếp tục?")) {
              await importBackupJSON(raw, "replace");
              showToast("Đã ghi đè toàn bộ dữ liệu từ file thành công!", "success");
              closeModal();
              refreshBackupBadge();
            }
          };

          mergeBtn.onclick = async () => {
            await importBackupJSON(raw, "merge");
            showToast("Đã hợp nhất dữ liệu thành công!", "success");
            closeModal();
            refreshBackupBadge();
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
    clearBtn.addEventListener("click", () => {
      clearModal.style.display = "flex";
    });

    if (cancelClearBtn) {
      cancelClearBtn.addEventListener("click", () => {
        clearModal.style.display = "none";
      });
    }

    if (confirmClearBtn) {
      confirmClearBtn.addEventListener("click", async () => {
        await clearAllPersonalData();
        localStorage.removeItem("easymeals_shopping_list");
        showToast("Đã xoá sạch toàn bộ dữ liệu cá nhân trên máy!", "info");
        clearModal.style.display = "none";
        refreshBackupBadge();
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
