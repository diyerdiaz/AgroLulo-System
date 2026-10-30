import re
from collections import defaultdict
from time import time

from flask import current_app, request

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


# --- Cabeceras de seguridad que acompañan cada respuesta ---
# 'unsafe-inline' sigue en la lista porque las plantillas traen <script> y
# onclick dentro del HTML. Todo lo demás solo puede venir de esta misma página.
POLITICA_CONTENIDO = '; '.join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


def agregar_cabeceras_seguridad(respuesta):
    """Le dice al navegador qué no debe permitir con esta página."""
    respuesta.headers['Content-Security-Policy'] = POLITICA_CONTENIDO
    respuesta.headers['X-Frame-Options'] = 'DENY'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if current_app.config.get('DETRAS_DE_HTTPS'):
        respuesta.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return respuesta


# --- Bloqueo por intentos fallidos de inicio de sesión (fuerza bruta) ---
# Guarda en memoria, por dirección IP, los intentos fallidos recientes.
# Como el servidor corre con un solo worker de Gunicorn (ver Dockerfile),
# un diccionario en memoria es suficiente: no hace falta una base de
# datos ni Redis aparte para esto.
INTENTOS_MAXIMOS = 5
VENTANA_SEGUNDOS = 15 * 60  # 15 minutos
BLOQUEO_SEGUNDOS = 15 * 60  # 15 minutos bloqueado tras agotar los intentos

_intentos_fallidos = defaultdict(list)  # ip -> lista de timestamps de intentos fallidos
_bloqueado_hasta = {}  # ip -> timestamp hasta el que queda bloqueada


def ip_solicitante():
    return request.remote_addr or 'desconocida'


def segundos_bloqueo_restante(ip):
    """Si la IP sigue bloqueada, devuelve cuántos segundos le faltan (>0).
    Si ya no está bloqueada, devuelve 0."""
    vence = _bloqueado_hasta.get(ip)
    if not vence:
        return 0
    restante = vence - time()
    if restante <= 0:
        _bloqueado_hasta.pop(ip, None)
        return 0
    return restante


def registrar_intento_fallido(ip):
    """Anota un intento fallido y, si ya se llegó al máximo permitido
    dentro de la ventana de tiempo, bloquea esa IP por un rato."""
    ahora = time()
    intentos = _intentos_fallidos[ip]
    intentos.append(ahora)
    # Descarta intentos viejos que ya salieron de la ventana de tiempo.
    intentos[:] = [t for t in intentos if ahora - t <= VENTANA_SEGUNDOS]

    if len(intentos) >= INTENTOS_MAXIMOS:
        _bloqueado_hasta[ip] = ahora + BLOQUEO_SEGUNDOS
        intentos.clear()


def limpiar_intentos(ip):
    """Se llama tras un inicio de sesión exitoso: borra el historial de
    intentos fallidos de esa IP."""
    _intentos_fallidos.pop(ip, None)
    _bloqueado_hasta.pop(ip, None)
