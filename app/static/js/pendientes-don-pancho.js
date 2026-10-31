// Don Pancho pregunta "¿Sí hizo lo que anotó?" por los trabajos del
// calendario que ya pasaron (o son de hoy) y no se han marcado como hechos.
// La ventana la arma templates/partials/pendientes_don_pancho.html.
(function () {
  'use strict';

  var raiz = document.getElementById('panchoPregunta');
  if (!raiz) return;

  var lista = raiz.querySelector('.pancho-pregunta-lista');
  var titulo = raiz.querySelector('.pancho-pregunta-titulo');
  var texto = raiz.querySelector('.pancho-pregunta-texto');
  var marcoAlguna = false;

  var FRASES_HECHO = ['¡Eso es, mano! ¡Qué verraquera!', '¡Así me gusta, juicioso!', '¡Bien hecho, hombre!'];
  var FRASES_TODAVIA = ['Hágale pues, que todavía hay tiempo 💪', 'Bueno, pero no lo deje pa\' mañana, ¿oyó?'];

  function azar(lista) {
    return lista[Math.floor(Math.random() * lista.length)];
  }

  function post(url) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
      }
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r;
    });
  }

  function cerrar() {
    raiz.classList.add('saliendo');
    document.removeEventListener('keydown', alTeclado);
    setTimeout(function () {
      raiz.remove();
      if (marcoAlguna && raiz.dataset.recargar === '1') location.reload();
    }, 250);
  }

  function despues() {
    // Si falla, lo peor que pasa es que vuelva a preguntar en otra página.
    post(raiz.dataset.urlDespues).catch(function () {});
    cerrar();
  }

  function quitarItem(item) {
    setTimeout(function () {
      item.classList.add('quitando');
      setTimeout(function () {
        item.remove();
        if (!lista.querySelector('.pancho-pregunta-item')) terminar();
      }, 300);
    }, 1100);
  }

  function terminar() {
    titulo.textContent = marcoAlguna ? '¡Qué verraquera, mano!' : '¡Bueno pues, a camellar!';
    texto.textContent = marcoAlguna
      ? 'Así me gusta, con el cultivo al día. ¡Siga así!'
      : 'Ya sabe lo que tiene pendiente. Cuando lo haga, márquelo en el calendario.';
    // Ya respondió todo: no se le vuelve a preguntar hoy.
    post(raiz.dataset.urlDespues).catch(function () {});
    setTimeout(cerrar, 1800);
  }

  function alTeclado(e) {
    if (e.key === 'Escape') despues();
  }

  raiz.addEventListener('click', function (e) {
    var boton = e.target.closest('[data-accion]');
    if (!boton) return;
    var accion = boton.dataset.accion;

    if (accion === 'despues') {
      despues();
      return;
    }

    var item = boton.closest('.pancho-pregunta-item');
    var respuesta = item.querySelector('.pancho-pregunta-respuesta');
    item.querySelectorAll('button').forEach(function (b) { b.disabled = true; });

    if (accion === 'hecha') {
      post(item.dataset.urlHecha).then(function () {
        marcoAlguna = true;
        item.classList.add('hecha');
        respuesta.textContent = azar(FRASES_HECHO);
        quitarItem(item);
      }).catch(function () {
        respuesta.textContent = 'Uy, no se pudo guardar. Intente otra vez.';
        item.querySelectorAll('button').forEach(function (b) { b.disabled = false; });
      });
    } else if (accion === 'todavia') {
      item.classList.add('todavia');
      respuesta.textContent = azar(FRASES_TODAVIA);
      quitarItem(item);
    }
  });

  document.addEventListener('keydown', alTeclado);

  // Si es la primera vez y está el recorrido de bienvenida, se espera a
  // que termine para no tapar uno con el otro.
  function mostrar() {
    if (document.body.classList.contains('don-pancho-activo')) {
      setTimeout(mostrar, 800);
      return;
    }
    raiz.classList.add('visible');
    var primero = raiz.querySelector('[data-accion="hecha"]');
    if (primero) primero.focus();
  }
  setTimeout(mostrar, 700);
})();
