// Don Pancho Lulero: recorrido guiado para quien entra por primera vez.
// Va señalando cada parte del Dashboard (los elementos con data-tour="...")
// y explica para qué sirve. Se puede saltar en cualquier momento, y se
// vuelve a abrir con el botón de la cara de Don Pancho.
(function () {
  'use strict';

  var raiz = document.getElementById('donPancho');
  var botonAyuda = document.getElementById('btnDonPancho');
  if (!raiz) return;

  var PASOS = [
    {
      pose: 'saludando',
      titulo: '¡Quiubo pues, mano!',
      texto: 'Yo soy Don Pancho Lulero, ¡y qué verraquera tenerlo por aquí en AgroLulo! ' +
             'Déjeme le muestro en un momentico cómo se maneja esto. Si ya se lo sabe, dele a "Saltar".'
    },
    {
      objetivo: 'menu',
      pose: 'senalando',
      titulo: 'Este es el menú',
      texto: 'Mire, aquí está todo, mano. Cada botón de este menú lo lleva a una parte de su finca. ' +
             'Vamos uno por uno, ¡que esto es facilito!'
    },
    {
      objetivo: 'cultivos',
      pose: 'senalando',
      titulo: 'Primero: sus Cultivos',
      texto: '¡Arranquemos por lo más importante! Aquí crea su lote de lulo. Los gastos, las cosechas ' +
             'y los pagos van pegados a un cultivo, así que créelo primerito, ¿oyó?'
    },
    {
      objetivo: 'calendario',
      pose: 'senalando',
      titulo: 'El Calendario',
      texto: 'Aquí anota lo que va haciendo en el cultivo: fumigadas, abonadas, cogidas… ' +
             '¡Pa\' que no se le pase ni una, hombre!'
    },
    {
      objetivo: 'gastos',
      pose: 'senalando',
      titulo: 'Los Gastos',
      texto: 'En Gastos apunta toda la plata que le mete al cultivo: abono, jornales, insumos. ' +
             '¡Peso que no se anota es peso que se pierde, mano!'
    },
    {
      objetivo: 'ingresos',
      pose: 'senalando',
      titulo: 'Los Ingresos',
      texto: 'Aquí registra sus cosechas: las canastillas, los kilos y a cómo los vendió. ' +
             '¡Ahí es donde se pone bueno el asunto!'
    },
    {
      objetivo: 'pagos',
      pose: 'senalando',
      titulo: 'Los Pagos',
      texto: 'Y en Pagos lleva la cuenta de lo que ya le pagaron y de lo que le quedan debiendo. ' +
             '¡Que nadie se le haga el loco con la platica!'
    },
    {
      objetivo: 'resumen',
      pose: 'pensando',
      titulo: 'El Dashboard General',
      texto: 'Y aquí ve el resumen de todo: cuánto ha invertido, cuánto ha ganado y si el lulo le está ' +
             'dejando ganancia. Esto se va llenando solito a medida que usted anota. ¡Tan bueno!'
    },
    {
      objetivo: 'perfil',
      pose: 'pensando',
      titulo: 'Ojo con esto',
      texto: 'Entre aquí a su cuenta y póngale su correo. Si un día se le olvida la contraseña, ' +
             'por ahí le mando el código pa\' recuperarla. ¡No lo deje pa\' después!'
    },
    {
      objetivo: 'ayuda',
      pose: 'saludando',
      titulo: '¡Listo, mano!',
      texto: 'Ya quedó enseñado. Si se le olvida algo, toque este botón con mi cara y vuelvo a explicarle. ' +
             '¡Hágale pues, que ese lulo no se cultiva solito!'
    }
  ];

  var sidebar = document.getElementById('sidebarLulo');
  var foco = raiz.querySelector('.don-pancho-foco');
  var globo = raiz.querySelector('.don-pancho-globo');
  var img = raiz.querySelector('.don-pancho-img');
  var titulo = raiz.querySelector('.don-pancho-titulo');
  var texto = raiz.querySelector('.don-pancho-texto');
  var progreso = raiz.querySelector('.don-pancho-progreso');
  var btnAnterior = raiz.querySelector('[data-accion="anterior"]');
  var btnSiguiente = raiz.querySelector('[data-accion="siguiente"]');

  var actual = 0;
  var abierto = false;
  var sidebarYaEstabaAbierto = false;
  var esperaPosicion = null;

  function esCelular() {
    return window.matchMedia('(max-width: 767.98px)').matches;
  }

  function elementoDe(paso) {
    if (!paso.objetivo) return null;
    // Puede haber más de uno con el mismo data-tour (por ejemplo, el botón
    // del menú en computador y el del encabezado en celular): se señala el
    // que de verdad se esté viendo en pantalla.
    var candidatos = document.querySelectorAll('[data-tour="' + paso.objetivo + '"]');
    for (var i = 0; i < candidatos.length; i++) {
      var r = candidatos[i].getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.right > 0 && r.left < window.innerWidth) {
        return candidatos[i];
      }
    }
    return null;
  }

  function estaEnElMenu(el) {
    return !!(el && sidebar && sidebar.contains(el));
  }

  function abrirMenu(abrir) {
    if (!sidebar) return;
    sidebar.classList.toggle('expanded', abrir);
  }

  function posicionar() {
    var paso = PASOS[actual];
    var el = elementoDe(paso);
    var margen = 12;

    raiz.classList.toggle('sin-foco', !el);
    if (!el) {
      foco.style.display = 'none';
      globo.classList.add('centrado');
      globo.style.left = globo.style.top = '';
      return;
    }

    var r = el.getBoundingClientRect();
    var holgura = 6;
    foco.style.display = 'block';
    foco.style.left = (r.left - holgura) + 'px';
    foco.style.top = (r.top - holgura) + 'px';
    foco.style.width = (r.width + holgura * 2) + 'px';
    foco.style.height = (r.height + holgura * 2) + 'px';

    // En celular el globo siempre va abajo, a lo ancho (lo maneja el CSS).
    if (esCelular()) {
      globo.classList.remove('centrado');
      globo.style.left = globo.style.top = '';
      return;
    }

    globo.classList.remove('centrado');
    var gw = globo.offsetWidth;
    var gh = globo.offsetHeight;
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    var left, top;

    if (r.right + margen + gw <= vw - margen) {          // a la derecha
      left = r.right + margen;
      top = r.top + r.height / 2 - gh / 2;
    } else if (r.left - margen - gw >= margen) {          // a la izquierda
      left = r.left - margen - gw;
      top = r.top + r.height / 2 - gh / 2;
    } else if (r.bottom + margen + gh <= vh - margen) {    // abajo
      left = r.left + r.width / 2 - gw / 2;
      top = r.bottom + margen;
    } else {                                               // arriba
      left = r.left + r.width / 2 - gw / 2;
      top = r.top - margen - gh;
    }

    left = Math.max(margen, Math.min(left, vw - gw - margen));
    top = Math.max(margen, Math.min(top, vh - gh - margen));
    globo.style.left = left + 'px';
    globo.style.top = top + 'px';
  }

  function mostrarPaso(i) {
    actual = i;
    var paso = PASOS[i];

    img.src = raiz.dataset['img' + paso.pose.charAt(0).toUpperCase() + paso.pose.slice(1)];
    titulo.textContent = paso.titulo;
    texto.textContent = paso.texto;
    progreso.textContent = (i + 1) + ' de ' + PASOS.length;
    btnAnterior.hidden = i === 0;
    btnSiguiente.innerHTML = i === PASOS.length - 1
      ? '¡De una! <i class="bi bi-check-lg"></i>'
      : 'Siguiente <i class="bi bi-arrow-right"></i>';

    // El menú lateral se abre solo mientras Don Pancho señala algo que
    // está adentro de él, y se cierra cuando ya no hace falta.
    var el = paso.objetivo ? document.querySelector('[data-tour="' + paso.objetivo + '"]') : null;
    var necesitaMenu = estaEnElMenu(el) && paso.objetivo !== 'menu';
    var cambiaMenu = sidebar && necesitaMenu !== sidebar.classList.contains('expanded');
    abrirMenu(necesitaMenu || (sidebarYaEstabaAbierto && !esCelular()));

    if (el && !estaEnElMenu(el) && el.scrollIntoView) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }

    globo.classList.remove('entrando');
    void globo.offsetWidth; // reinicia la animación de entrada
    globo.classList.add('entrando');

    // Si el menú se está abriendo o cerrando, se espera a que termine la
    // animación (0.35 s en style.css) antes de medir dónde quedó todo.
    clearTimeout(esperaPosicion);
    posicionar();
    esperaPosicion = setTimeout(posicionar, cambiaMenu || el ? 400 : 0);
    btnSiguiente.focus();
  }

  function abrir() {
    if (abierto) return;
    abierto = true;
    sidebarYaEstabaAbierto = !!(sidebar && sidebar.classList.contains('expanded'));
    raiz.hidden = false;
    document.body.classList.add('don-pancho-activo');
    mostrarPaso(0);
  }

  function cerrar() {
    if (!abierto) return;
    abierto = false;
    clearTimeout(esperaPosicion);
    raiz.hidden = true;
    document.body.classList.remove('don-pancho-activo');
    abrirMenu(sidebarYaEstabaAbierto && !esCelular());
    marcarVisto();
    if (botonAyuda) botonAyuda.focus();
  }

  function marcarVisto() {
    if (raiz.dataset.mostrar !== '1') return;
    raiz.dataset.mostrar = '0';
    fetch(raiz.dataset.urlVisto, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
    })
      .catch(function () { /* si falla, la próxima vez vuelve a salir; no pasa nada grave */ });
  }

  raiz.addEventListener('click', function (e) {
    var boton = e.target.closest('[data-accion]');
    if (!boton) return;
    var accion = boton.dataset.accion;
    if (accion === 'saltar') cerrar();
    else if (accion === 'anterior' && actual > 0) mostrarPaso(actual - 1);
    else if (accion === 'siguiente') {
      if (actual < PASOS.length - 1) mostrarPaso(actual + 1);
      else cerrar();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (!abierto) return;
    if (e.key === 'Escape') cerrar();
    else if (e.key === 'ArrowRight' && actual < PASOS.length - 1) mostrarPaso(actual + 1);
    else if (e.key === 'ArrowLeft' && actual > 0) mostrarPaso(actual - 1);
  });

  window.addEventListener('resize', function () { if (abierto) posicionar(); });
  window.addEventListener('scroll', function () { if (abierto) posicionar(); }, true);

  if (botonAyuda) botonAyuda.addEventListener('click', abrir);

  if (raiz.dataset.mostrar === '1') {
    // Un respiro para que la página termine de pintarse antes de saludar.
    setTimeout(abrir, 600);
  }
})();
