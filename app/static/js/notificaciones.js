/* Notificaciones flotantes: se cierran solas después de unos segundos
   (pausando mientras el mouse está encima) o con la X. */
document.querySelectorAll('.notificacion').forEach((notificacion, indice) => {
  const duracion = parseInt(notificacion.dataset.duracion, 10) || 5000;
  const barra = notificacion.querySelector('.notificacion-progreso');
  let restante = duracion;
  let inicio;
  let temporizador;

  const cerrar = () => {
    clearTimeout(temporizador);
    notificacion.classList.add('saliendo');
    notificacion.addEventListener('animationend', () => notificacion.remove(), { once: true });
  };

  const correr = () => {
    inicio = Date.now();
    barra.style.transition = `transform ${restante}ms linear`;
    barra.style.transform = 'scaleX(0)';
    temporizador = setTimeout(cerrar, restante);
  };

  const pausar = () => {
    if (!inicio) return;
    clearTimeout(temporizador);
    restante -= Date.now() - inicio;
    const escala = Math.max(restante, 0) / duracion;
    barra.style.transition = 'none';
    barra.style.transform = `scaleX(${escala})`;
  };

  notificacion.querySelector('.notificacion-cerrar').addEventListener('click', cerrar);
  notificacion.addEventListener('mouseenter', pausar);
  notificacion.addEventListener('mouseleave', correr);

  // Pequeño desfase entre varias notificaciones para que no entren todas a la vez.
  notificacion.style.animationDelay = `${indice * 120}ms`;
  requestAnimationFrame(() => requestAnimationFrame(correr));
});
