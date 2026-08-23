/*
 * Animación de carga global de AgroLulo System.
 * Se inyecta una sola vez (por página) y usa el mismo diseño neón del fondo
 * (colores/temas ya definidos en style.css), para que combine con la página.
 * Se activa automáticamente al hacer clic en enlaces que navegan y al enviar
 * formularios; también puede llamarse manualmente con showPageLoading().
 */
(function () {
  function ensureOverlay() {
    let overlay = document.getElementById('pageLoadingOverlay');
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = 'pageLoadingOverlay';
    overlay.className = 'page-loading-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML =
      '<div class="page-loading-box">' +
        '<div class="page-loading-ring-wrap">' +
          '<div class="page-loading-ring"></div>' +
          '<div class="page-loading-logo"><i class="bi bi-tree-fill"></i></div>' +
        '</div>' +
        '<div class="page-loading-text">Cargando<span>...</span></div>' +
      '</div>';
    document.body.appendChild(overlay);
    return overlay;
  }

  function showPageLoading() {
    ensureOverlay().classList.add('is-active');
  }

  function hidePageLoading() {
    const overlay = document.getElementById('pageLoadingOverlay');
    if (overlay) overlay.classList.remove('is-active');
  }

  // Disponibles globalmente por si alguna página quiere invocarlas manualmente
  window.showPageLoading = showPageLoading;
  window.hidePageLoading = hidePageLoading;

  document.addEventListener('DOMContentLoaded', function () {
    ensureOverlay();

    // Cualquier enlace que navegue a otra página (excluye anclas "#",
    // "javascript:void(0)", enlaces con target="_blank" y disparadores
    // de Bootstrap como modales/dropdowns, que no cargan una página nueva)
    document.addEventListener('click', function (e) {
      const link = e.target.closest('a');
      if (!link) return;

      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
      if (link.target === '_blank') return;
      if (link.hasAttribute('data-bs-toggle') || link.hasAttribute('data-bs-dismiss')) return;
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;

      showPageLoading();
    });

    // Cualquier formulario que se envíe (login, registrar cultivo,
    // agregar/eliminar etiqueta del calendario, filtros, etc.)
    document.addEventListener('submit', function (e) {
      if (e.target && e.target.tagName === 'FORM') {
        showPageLoading();
      }
    });
  });

  // Si el usuario regresa con el botón "atrás" del navegador (bfcache),
  // aseguramos que el overlay no se quede visible.
  window.addEventListener('pageshow', function () {
    hidePageLoading();
  });
})();
