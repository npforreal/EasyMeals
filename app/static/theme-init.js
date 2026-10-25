/* Apply the saved theme and palette before first paint to avoid a flash. */
try {
  var t = localStorage.getItem("theme");
  if (t === "light" || t === "dark") {
    document.documentElement.setAttribute("data-theme", t);
  } else if (t === "system") {
    document.documentElement.removeAttribute("data-theme");
  }
  var p = localStorage.getItem("palette");
  if (p && ["green", "terracotta", "ocean", "plum", "peach"].indexOf(p) !== -1) {
    document.documentElement.setAttribute("data-palette", p);
  }
} catch (e) {}
