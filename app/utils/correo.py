import os
import re
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from email.utils import make_msgid

from flask import current_app, render_template

_PATRON_CORREO = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def correo_valido(correo):
    """True si el texto tiene forma de correo electrónico (algo@dominio.algo)."""
    return bool(correo) and len(correo) <= 120 and bool(_PATRON_CORREO.match(correo))


def enviar_correo(destino, asunto, texto, html=None, imagenes=None):
    """
    Envía un correo usando los datos MAIL_* del .env (por defecto, el SMTP
    de Gmail con STARTTLS en el puerto 587). Lanza RuntimeError si el envío
    de correos todavía no está configurado, y deja pasar los errores de
    SMTP para que quien llama decida qué mostrarle al usuario.

    imagenes: lista de (cid, ruta_del_archivo) que van incrustadas dentro
    del correo y se usan en el HTML como <img src="cid:...">. Así se ven
    sin depender de ningún enlace ni del dominio de la página.
    """
    cfg = current_app.config
    if not cfg.get('MAIL_USERNAME') or not cfg.get('MAIL_PASSWORD'):
        raise RuntimeError('El envío de correos no está configurado (faltan MAIL_USERNAME / MAIL_PASSWORD en el .env).')

    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = f"AgroLulo System <{cfg.get('MAIL_SENDER') or cfg['MAIL_USERNAME']}>"
    mensaje['To'] = destino
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype='html')
        parte_html = mensaje.get_payload()[-1]
        for cid, ruta in imagenes or []:
            with open(ruta, 'rb') as archivo:
                parte_html.add_related(archivo.read(), 'image', 'jpeg', cid=f'<{cid}>')

    with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=15) as servidor:
        # Sin este contexto, starttls() no revisa el certificado del servidor
        # y alguien en la misma red podría hacerse pasar por Gmail para
        # robarse MAIL_PASSWORD. Con él, la conexión falla antes del login.
        servidor.starttls(context=ssl.create_default_context())
        servidor.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        servidor.send_message(mensaje)


def armar_correo_recuperacion(nombre_usuario, codigo, minutos_validez):
    """
    Devuelve (asunto, texto, html, imagenes) del correo con el código de 6
    dígitos. El HTML sale de templates/correos/recuperar_contrasena.html.
    """
    asunto = f'{codigo} es tu código para recuperar tu contraseña de AgroLulo'
    texto = (
        f'Hola, {nombre_usuario}.\n\n'
        f'Tu código para recuperar la contraseña de AgroLulo System es: {codigo}\n\n'
        f'El código vence en {minutos_validez} minutos y solo se puede usar una vez.\n'
        'Si tú no pediste este código, ignora este correo: tu contraseña no ha cambiado.\n'
    )
    cid_encabezado = make_msgid(domain='agrolulo')[1:-1]
    html = render_template(
        'correos/recuperar_contrasena.html',
        nombre=nombre_usuario,
        codigo=codigo,
        minutos=minutos_validez,
        anio=date.today().year,
        cid_encabezado=cid_encabezado,
    )
    ruta_encabezado = os.path.join(current_app.root_path, 'static', 'img', 'correo_encabezado.jpg')
    return asunto, texto, html, [(cid_encabezado, ruta_encabezado)]


def enviar_codigo_recuperacion(destino, nombre_usuario, codigo, minutos_validez):
    """Arma y envía el correo con el código de 6 dígitos para recuperar la contraseña."""
    asunto, texto, html, imagenes = armar_correo_recuperacion(nombre_usuario, codigo, minutos_validez)
    enviar_correo(destino, asunto, texto, html, imagenes)
