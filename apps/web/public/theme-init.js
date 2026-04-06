/**
 * Anti-FOUC: aplica data-theme antes do React (sem inline script no HTML → CSP mais estrita).
 */
(function () {
  try {
    var k = "otm.web.themePreference";
    var v = localStorage.getItem(k);
    var resolved;
    if (v === "light") resolved = "light";
    else if (v === "dark") resolved = "dark";
    else if (v === "system")
      resolved = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    else resolved = "dark";
    document.documentElement.setAttribute("data-theme", resolved);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
