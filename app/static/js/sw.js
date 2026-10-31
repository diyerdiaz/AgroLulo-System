// Service worker de la app instalable. Solo guarda archivos públicos y la
// pantalla "sin conexión". Las páginas de una cuenta NUNCA se guardan aquí:
// quedarían en el celular aunque la persona cierre la sesión.
var CACHE = 'agrolulo-v1';
var ARCHIVOS = [
  '/offline',
  '/static/bootstrap/css/bootstrap.min.css',
  '/static/css/bootstrap-icons.min.css',
  '/static/css/style.css',
  '/static/img/agrolulo-logo.svg'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (cache) {
    return cache.addAll(ARCHIVOS);
  }).then(function () {
    return self.skipWaiting();
  }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (nombres) {
    return Promise.all(nombres.filter(function (n) { return n !== CACHE; }).map(function (n) {
      return caches.delete(n);
    }));
  }).then(function () {
    return self.clients.claim();
  }));
});

self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(function () {
      return caches.match('/offline');
    }));
    return;
  }

  // Con internet siempre se usa la versión nueva; sin internet, la guardada.
  if (url.pathname.indexOf('/static/') === 0) {
    e.respondWith(fetch(e.request).catch(function () {
      return caches.match(e.request);
    }));
  }
});
