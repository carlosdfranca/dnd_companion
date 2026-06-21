document.addEventListener("DOMContentLoaded", function () {
  var btn  = document.getElementById("theme-toggle");
  var icon = document.getElementById("theme-icon");
  var html = document.documentElement;

  function applyTheme(theme) {
    html.setAttribute("data-theme", theme);
    html.setAttribute("data-bs-theme", theme);
    try { localStorage.setItem("belmora-theme", theme); } catch(e) {}
    if (icon) {
      icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
    }
    if (btn) {
      btn.title = theme === "dark" ? "Mudar para modo claro" : "Mudar para modo escuro";
    }
  }

  // Sincroniza o ícone com o tema já aplicado pelo script inline do <head>
  applyTheme(html.getAttribute("data-theme") || "dark");

  if (btn) {
    btn.addEventListener("click", function () {
      var next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }
});
