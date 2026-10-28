/* Animaciones de la landing page:
   1. Efecto de escritura del título (respeta su diseño original).
   2. Aparición de tarjetas y títulos al bajar por la página.
   3. "Cómo funciona": los pasos se encienden uno a uno con una flecha
      que se dibuja hacia el siguiente.
   Si la persona tiene desactivadas las animaciones en su sistema, todo se
   muestra de una vez, sin efectos. */
(function () {
  const sinAnimaciones = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // La landing siempre usa el verde de la marca en el fondo animado, aunque
  // la persona haya elegido otro tema (azul/naranja) dentro de la app.
  if (window.updateCanvasTheme) window.updateCanvasTheme('green');

  // ---------- 1. Efecto de escritura ----------
  function escribirTitulo(titulo) {
    // Guarda el título original por partes (texto normal y el <span> verde)
    const partes = Array.from(titulo.childNodes)
      .map(nodo => ({
        texto: nodo.textContent.replace(/\s+/g, ' '),
        molde: nodo.nodeType === Node.ELEMENT_NODE ? nodo.cloneNode(false) : null,
      }))
      .filter(parte => parte.texto.trim() !== '');
    if (!partes.length) return;
    partes[0].texto = partes[0].texto.trimStart();
    partes[partes.length - 1].texto = partes[partes.length - 1].texto.trimEnd();

    // Reserva el alto final para que la página no salte mientras escribe
    titulo.style.minHeight = titulo.offsetHeight + 'px';
    titulo.textContent = '';

    const cursor = document.createElement('span');
    cursor.className = 'cursor-escritura';
    cursor.setAttribute('aria-hidden', 'true');

    const destinos = partes.map(parte => {
      const nodo = parte.molde || document.createTextNode('');
      if (parte.molde) parte.molde.textContent = '';
      titulo.appendChild(nodo);
      return nodo;
    });
    titulo.appendChild(cursor);

    let parte = 0;
    let letra = 0;
    const escribir = () => {
      if (parte >= partes.length) {
        titulo.classList.add('escritura-terminada');
        return;
      }
      destinos[parte].textContent += partes[parte].texto[letra];
      letra += 1;
      if (letra >= partes[parte].texto.length) {
        parte += 1;
        letra = 0;
      }
      setTimeout(escribir, 55);
    };
    setTimeout(escribir, 350);
  }

  // ---------- 3. Pasos con flechas ----------
  function encenderPasos(contenedor) {
    const elementos = Array.from(contenedor.children); // paso, flecha, paso, flecha...
    elementos.forEach((elemento, i) => {
      setTimeout(() => elemento.classList.add('activo'), i * 450);
    });
  }

  // ---------- 2. Aparición al bajar ----------
  function iniciar() {
    const titulo = document.querySelector('[data-escritura]');
    const pasos = document.querySelector('[data-pasos]');
    const revelables = document.querySelectorAll('.revelar');

    if (sinAnimaciones || !('IntersectionObserver' in window)) {
      revelables.forEach(el => el.classList.add('visible'));
      if (pasos) Array.from(pasos.children).forEach(el => el.classList.add('activo'));
      return;
    }

    if (titulo) escribirTitulo(titulo);

    const observador = new IntersectionObserver((entradas, obs) => {
      entradas.forEach(entrada => {
        if (!entrada.isIntersecting) return;
        const el = entrada.target;
        if (el.hasAttribute('data-pasos')) {
          encenderPasos(el);
        } else {
          el.classList.add('visible');
          // Al terminar de aparecer vuelve a su estilo normal (p. ej. el
          // efecto al pasar el mouse por encima de las tarjetas).
          el.addEventListener('transitionend', () => el.classList.remove('revelar'), { once: true });
        }
        obs.unobserve(el);
      });
    }, { threshold: 0.18, rootMargin: '0px 0px -8% 0px' });

    revelables.forEach(el => observador.observe(el));
    if (pasos) observador.observe(pasos);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
