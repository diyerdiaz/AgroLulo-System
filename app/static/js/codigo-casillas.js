/* Código de verificación en 6 casillas (una por dígito):
   - al escribir un dígito pasa sola a la siguiente casilla,
   - Borrar vuelve a la anterior, y las flechas mueven entre casillas,
   - al pegar el código (o si el celular lo autocompleta) llena las 6,
   - antes de enviar junta los 6 dígitos en el campo oculto "codigo". */
document.querySelectorAll('[data-codigo-casillas]').forEach(formulario => {
  const casillas = Array.from(formulario.querySelectorAll('.codigo-casilla'));
  const oculto = formulario.querySelector('input[name="codigo"]');
  const aviso = formulario.querySelector('.codigo-casillas-error');

  const repartir = (texto, desde) => {
    const digitos = texto.replace(/\D/g, '').split('');
    let i = desde;
    while (digitos.length && i < casillas.length) {
      casillas[i].value = digitos.shift();
      casillas[i].classList.add('llena');
      i += 1;
    }
    casillas[Math.min(i, casillas.length - 1)].focus();
  };

  casillas.forEach((casilla, indice) => {
    casilla.addEventListener('input', () => {
      const valor = casilla.value.replace(/\D/g, '');
      casilla.value = '';
      casilla.classList.remove('llena');
      if (valor) repartir(valor, indice); // varios dígitos = pegado o autocompletado
      if (aviso) aviso.classList.add('d-none');
    });

    casilla.addEventListener('keydown', evento => {
      if (evento.key === 'Backspace' && !casilla.value && indice > 0) {
        evento.preventDefault();
        casillas[indice - 1].value = '';
        casillas[indice - 1].classList.remove('llena');
        casillas[indice - 1].focus();
      } else if (evento.key === 'ArrowLeft' && indice > 0) {
        casillas[indice - 1].focus();
      } else if (evento.key === 'ArrowRight' && indice < casillas.length - 1) {
        casillas[indice + 1].focus();
      }
    });

    casilla.addEventListener('paste', evento => {
      evento.preventDefault();
      repartir((evento.clipboardData || window.clipboardData).getData('text'), indice);
    });

    casilla.addEventListener('focus', () => casilla.select());
  });

  formulario.addEventListener('submit', evento => {
    const codigo = casillas.map(c => c.value).join('');
    if (!/^\d{6}$/.test(codigo)) {
      evento.preventDefault();
      if (aviso) aviso.classList.remove('d-none');
      casillas[casillas.findIndex(c => !c.value)]?.focus();
      return;
    }
    oculto.value = codigo;
  });
});
