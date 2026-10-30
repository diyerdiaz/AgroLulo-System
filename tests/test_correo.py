import smtplib
import ssl

import pytest

from app.utils import correo


class SMTPFalso:
    """Reemplaza a smtplib.SMTP: anota lo que se le pide y no abre ninguna conexión."""
    llamadas = []
    contexto = None

    def __init__(self, servidor, puerto, timeout=None):
        SMTPFalso.llamadas = []
        SMTPFalso.contexto = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        SMTPFalso.llamadas.append('starttls')
        SMTPFalso.contexto = context

    def login(self, usuario, clave):
        SMTPFalso.llamadas.append('login')

    def send_message(self, mensaje):
        SMTPFalso.llamadas.append('send_message')


@pytest.fixture
def smtp_falso(app, monkeypatch):
    monkeypatch.setattr(correo.smtplib, 'SMTP', SMTPFalso)
    app.config.update(MAIL_USERNAME='cuenta@gmail.com', MAIL_PASSWORD='clave-app', MAIL_SENDER='')
    return SMTPFalso


def test_valida_el_certificado_del_servidor_antes_de_iniciar_sesion(app, smtp_falso):
    with app.app_context():
        correo.enviar_correo('destino@correo.com', 'Asunto', 'Texto')

    assert smtp_falso.llamadas == ['starttls', 'login', 'send_message']
    assert smtp_falso.contexto.verify_mode == ssl.CERT_REQUIRED
    assert smtp_falso.contexto.check_hostname is True


def test_sin_credenciales_no_intenta_conectarse(app, monkeypatch):
    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError('No debía conectarse al servidor')

    monkeypatch.setattr(smtplib, 'SMTP', no_debe_llamarse)
    app.config.update(MAIL_USERNAME='', MAIL_PASSWORD='')
    with app.app_context(), pytest.raises(RuntimeError):
        correo.enviar_correo('destino@correo.com', 'Asunto', 'Texto')
