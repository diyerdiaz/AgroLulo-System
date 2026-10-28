/* Reglas de contraseña: las mismas que valida el servidor en
   app/utils/seguridad.py. Pinta en verde cada regla que se cumple. */
function reglasContrasena(password, usuario) {
  const u = (usuario || '').trim().toLowerCase();
  return {
    largo: password.length >= 8 && password.length <= 128,
    mayuscula: /[A-ZÁÉÍÓÚÑ]/.test(password),
    minuscula: /[a-záéíóúñ]/.test(password),
    numero: /\d/.test(password),
    usuario: !(u.length >= 3 && password.toLowerCase().includes(u)),
  };
}

function pintarReglas(listaId, password, usuario) {
  const reglas = reglasContrasena(password, usuario);
  document.querySelectorAll('#' + listaId + ' li').forEach(li => {
    const ok = reglas[li.dataset.regla];
    li.classList.toggle('cumple', ok);
    li.querySelector('i').className = ok ? 'bi bi-check-circle-fill' : 'bi bi-circle';
  });
  return Object.values(reglas).every(Boolean);
}
