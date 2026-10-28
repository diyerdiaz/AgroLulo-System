import re

CONTRASENA_MIN = 8
CONTRASENA_MAX = 128


def errores_contrasena(contrasena, nombre_usuario=None):
    """
    Revisa que una contraseña nueva cumpla las reglas de seguridad y
    devuelve la lista de reglas que NO cumple (vacía si está bien). Se usa
    en todos los lugares donde se crea o cambia una contraseña: registro,
    recuperación con código, Mi Cuenta y creación de cuentas del admin.
    """
    contrasena = contrasena or ''
    errores = []
    if len(contrasena) < CONTRASENA_MIN:
        errores.append(f'tener al menos {CONTRASENA_MIN} caracteres')
    if len(contrasena) > CONTRASENA_MAX:
        errores.append(f'tener máximo {CONTRASENA_MAX} caracteres')
    if not re.search(r'[A-ZÁÉÍÓÚÑ]', contrasena):
        errores.append('tener al menos una letra mayúscula')
    if not re.search(r'[a-záéíóúñ]', contrasena):
        errores.append('tener al menos una letra minúscula')
    if not re.search(r'\d', contrasena):
        errores.append('tener al menos un número')
    if nombre_usuario and len(nombre_usuario) >= 3 and nombre_usuario.lower() in contrasena.lower():
        errores.append('no contener tu nombre de usuario')
    return errores


def mensaje_contrasena_invalida(errores):
    """Arma un solo mensaje claro a partir de la lista de reglas que faltan."""
    return 'La contraseña debe ' + ', '.join(errores[:-1]) + (' y ' if len(errores) > 1 else '') + errores[-1] + '.'
