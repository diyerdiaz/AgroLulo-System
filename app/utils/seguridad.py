import ipaddress
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from time import monotonic

from flask import abort, current_app, request
from flask_login import current_user

from app import db
from app.models.intento_acceso import IntentoAcceso

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


NOMBRE_MIN = 3
NOMBRE_MAX = 30
_PATRON_NOMBRE = re.compile(r'^[\w.-]+(?: [\w.-]+)*$')
# Nadie puede hacerse pasar por la administración con estos nombres.
_NOMBRES_RESERVADOS = {'admin', 'administrador', 'administrator', 'root', 'soporte'}


def error_nombre_usuario(nombre):
    """Devuelve qué tiene de malo un nombre de usuario nuevo, o None si está bien."""
    if not NOMBRE_MIN <= len(nombre) <= NOMBRE_MAX:
        return f'El nombre de usuario debe tener entre {NOMBRE_MIN} y {NOMBRE_MAX} caracteres.'
    if not _PATRON_NOMBRE.match(nombre):
        return 'El nombre de usuario solo puede tener letras, números, espacios, puntos, guiones y guiones bajos.'
    if nombre.lower() in _NOMBRES_RESERVADOS:
        return 'Ese nombre de usuario no está disponible.'
    return None


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


def limitar_formularios_de_texto():
    """Rechaza con 413 los formularios de texto demasiado grandes."""
    if (request.mimetype == 'application/x-www-form-urlencoded'
            and (request.content_length or 0) > current_app.config['MAX_FORMULARIO_TEXTO']):
        abort(413)


def agregar_cabeceras_seguridad(respuesta):
    """Le dice al navegador qué no debe permitir con esta página."""
    respuesta.headers['Content-Security-Policy'] = POLITICA_CONTENIDO
    respuesta.headers['X-Frame-Options'] = 'DENY'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Las páginas de una cuenta no se guardan en el navegador: en un celular
    # o computador compartido, otra persona podría verlas con el botón Atrás.
    if current_user.is_authenticated and request.endpoint != 'static':
        respuesta.headers['Cache-Control'] = 'no-store'
    if current_app.config.get('DETRAS_DE_HTTPS'):
        respuesta.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return respuesta


# --- Límites de intentos para frenar ataques automáticos ---
# accion: (máximo de intentos, segundos). Al llegar al máximo, esa IP o cuenta
# queda bloqueada hasta que pase ese tiempo desde su último intento.
LIMITES = {
    'login': (5, 15 * 60),
    'registro': (5, 60 * 60),
    'recuperar': (10, 60 * 60),
    'codigo': (10, 24 * 60 * 60),
    # Más alto que el de la IP: si fuera igual, un atacante podría agotarlo
    # a propósito y dejar a la persona sin poder recuperar su cuenta.
    'codigo_cuenta': (50, 24 * 60 * 60),
    # Bots: tocar rutas trampa varias veces y, cuando ya cayó, 1 hora afuera.
    'sondeo': (3, 60 * 60),
    'bloqueo_ip': (1, 60 * 60),
}
DIAS_CONSERVAR_INTENTOS = 2


def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ip_solicitante():
    return request.remote_addr or 'desconocida'


def segundos_bloqueo_restante(clave, accion='login'):
    """Si la IP o cuenta sigue bloqueada para esa acción, devuelve cuántos
    segundos le faltan (>0). Si no está bloqueada, devuelve 0."""
    maximo, segundos = LIMITES[accion]
    ahora = _ahora()
    intentos = (IntentoAcceso.query
                .filter(IntentoAcceso.accion == accion, IntentoAcceso.clave == clave,
                        IntentoAcceso.fecha > ahora - timedelta(seconds=segundos))
                .order_by(IntentoAcceso.fecha.desc()).limit(maximo).all())
    if len(intentos) < maximo:
        return 0
    return max(0, segundos - (ahora - intentos[0].fecha).total_seconds())


def registrar_intento(clave, accion='login'):
    """Anota un intento y aprovecha para borrar los que ya no sirven."""
    ahora = _ahora()
    IntentoAcceso.query.filter(
        IntentoAcceso.fecha < ahora - timedelta(days=DIAS_CONSERVAR_INTENTOS)
    ).delete(synchronize_session=False)
    db.session.add(IntentoAcceso(accion=accion, clave=clave, fecha=ahora))
    db.session.commit()


def limpiar_intentos(clave, accion='login'):
    """Se llama cuando la persona demostró ser quien dice ser: borra sus
    intentos fallidos de esa acción."""
    IntentoAcceso.query.filter_by(accion=accion, clave=clave).delete(synchronize_session=False)
    db.session.commit()


# --- Bloqueo automático de bots ---
# Direcciones que esta página no tiene y que los bots prueban buscando huecos
# de otros programas. Una persona normal nunca llega a ellas.
_RUTAS_TRAMPA = re.compile(
    r'\.(php|asp|aspx|env|git|sql|bak|aws)\b|wp-|wordpress|phpmyadmin|xmlrpc|cgi-bin',
    re.IGNORECASE,
)
# Programas de ataque que se identifican a sí mismos.
_PROGRAMAS_DE_ATAQUE = re.compile(
    r'sqlmap|nikto|masscan|zgrab|nmap|nuclei|wpscan|dirbuster|gobuster|acunetix|nessus|hydra',
    re.IGNORECASE,
)
# Peticiones por minuto de una misma IP, sin contar imágenes, CSS y JavaScript.
# Vive en memoria porque guardar cada visita en la base de datos la haría lenta.
PETICIONES_POR_MINUTO = 120
_MAXIMO_IPS_EN_MEMORIA = 10000
_visitas_recientes = defaultdict(deque)


def _ip_bloqueable(ip):
    """Sin un proxy delante, todas las visitas parecen venir de la misma IP y
    se bloquearía a todo el mundo. Las direcciones internas tampoco se tocan."""
    if not current_app.config.get('DETRAS_DE_HTTPS'):
        return False
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _demasiadas_visitas(ip):
    if len(_visitas_recientes) > _MAXIMO_IPS_EN_MEMORIA:
        _visitas_recientes.clear()
    ahora = monotonic()
    visitas = _visitas_recientes[ip]
    while visitas and ahora - visitas[0] > 60:
        visitas.popleft()
    visitas.append(ahora)
    return len(visitas) > PETICIONES_POR_MINUTO


def bloquear_bots():
    """Corta las IP que se comportan como bots, antes de hacer cualquier otro
    trabajo. Los bloqueos vencen solos; `flask --app run desbloquear-ip` los
    quita antes de tiempo."""
    ip = ip_solicitante()
    if request.endpoint == 'static' or not _ip_bloqueable(ip):
        return
    if segundos_bloqueo_restante(ip, 'bloqueo_ip') > 0:
        abort(403)

    if (_PROGRAMAS_DE_ATAQUE.search(request.user_agent.string) or _demasiadas_visitas(ip)):
        registrar_intento(ip, 'bloqueo_ip')
        current_app.logger.warning('IP bloqueada por 1 hora: %s', ip)
        abort(403)

    if _RUTAS_TRAMPA.search(request.path):
        registrar_intento(ip, 'sondeo')
        if segundos_bloqueo_restante(ip, 'sondeo') > 0:
            registrar_intento(ip, 'bloqueo_ip')
            current_app.logger.warning('IP bloqueada por 1 hora: %s', ip)
        abort(404)
