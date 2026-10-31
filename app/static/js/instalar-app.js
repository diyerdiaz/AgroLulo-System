// Registra el service worker y maneja los botones "Instalar app"
// (partials/instalar_app.html).
(function () {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function () { /* la página funciona igual sin esto */ });
  }

  var yaInstalada = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  var esIphone = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var aviso = null;

  function mostrarBotones() {
    document.querySelectorAll('[data-instalar-app]').forEach(function (caja) {
      caja.classList.remove('d-none');
    });
  }

  if (yaInstalada) return;

  // Chrome avisa cuando la página se puede instalar; se guarda ese aviso
  // para abrirlo cuando la persona toque el botón.
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    aviso = e;
    mostrarBotones();
  });

  window.addEventListener('appinstalled', function () {
    document.querySelectorAll('[data-instalar-app]').forEach(function (caja) {
      caja.classList.add('d-none');
    });
  });

  // El iPhone no tiene ese aviso: se instala a mano desde Safari.
  if (esIphone) mostrarBotones();

  document.addEventListener('click', function (e) {
    var boton = e.target.closest('[data-instalar-boton]');
    if (!boton) return;
    if (aviso) {
      aviso.prompt();
      aviso = null;
      return;
    }
    boton.parentElement.querySelector('[data-instalar-ayuda]').classList.remove('d-none');
  });
})();
