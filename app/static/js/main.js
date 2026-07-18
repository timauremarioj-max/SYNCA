/* SYNCA — Comportamiento del menú lateral en dispositivos móviles */
(function () {
  var btn = document.getElementById('btn-menu');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');

  if (!btn || !sidebar || !overlay) return;

  function abrirMenu() {
    sidebar.classList.add('abierto');
    overlay.classList.add('activo');
    btn.setAttribute('aria-expanded', 'true');
  }

  function cerrarMenu() {
    sidebar.classList.remove('abierto');
    overlay.classList.remove('activo');
    btn.setAttribute('aria-expanded', 'false');
  }

  btn.addEventListener('click', function () {
    if (sidebar.classList.contains('abierto')) {
      cerrarMenu();
    } else {
      abrirMenu();
    }
  });

  overlay.addEventListener('click', cerrarMenu);

  // Cerrar el menú al elegir una opción (útil en móvil)
  sidebar.querySelectorAll('a').forEach(function (enlace) {
    enlace.addEventListener('click', cerrarMenu);
  });

  // Si la pantalla vuelve a tamaño de escritorio, aseguramos que
  // el menú quede en su estado normal (visible, sin overlay)
  window.addEventListener('resize', function () {
    if (window.innerWidth > 900) {
      cerrarMenu();
    }
  });
})();
