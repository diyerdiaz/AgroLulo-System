from datetime import timedelta

import pytest

from app import db
from app.models.codigo_recuperacion import CodigoRecuperacion
from app.routes import auth
from tests.conftest import crear_usuario


@pytest.fixture
def correos(monkeypatch):
    """Reemplaza el envío real de correos: guarda lo que se habría enviado."""
    enviados = []

    def falso(destino, nombre_usuario, codigo, minutos_validez):
        enviados.append({'destino': destino, 'codigo': codigo})

    monkeypatch.setattr(auth, 'enviar_codigo_recuperacion', falso)
    return enviados


@pytest.fixture
def cuenta(app):
    return crear_usuario('lulero', clave='vieja123', correo='lulero@ejemplo.com')


def pedir_codigo(client, usuario_o_correo):
    return client.post('/recuperar', data={'usuarioCorreo': usuario_o_correo})


def verificar(client, codigo, nueva='nueva456', confirmar=None):
    return client.post('/recuperar/verificar', data={
        'codigo': codigo, 'nueva_password': nueva,
        'confirmar_password': nueva if confirmar is None else confirmar,
    }, follow_redirects=True)


def test_login_muestra_enlace_de_recuperacion(client):
    assert 'Olvidaste tu contraseña'.encode() in client.get('/login').data


@pytest.mark.parametrize('dato', ['lulero', 'LULERO@ejemplo.com'])
def test_envia_codigo_por_usuario_o_correo(client, cuenta, correos, dato):
    response = pedir_codigo(client, dato)
    assert 'te enviamos'.encode() in response.data
    assert len(correos) == 1
    assert correos[0]['destino'] == 'lulero@ejemplo.com'
    assert len(correos[0]['codigo']) == 6 and correos[0]['codigo'].isdigit()


def test_codigo_se_guarda_encriptado(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    registro = CodigoRecuperacion.query.filter_by(idUser=cuenta.idUser).one()
    assert registro.codigo_hash != correos[0]['codigo']


def test_cuenta_inexistente_muestra_el_mismo_mensaje(client, correos):
    response = pedir_codigo(client, 'nadie')
    assert 'te enviamos'.encode() in response.data
    assert correos == []


def test_cuenta_sin_correo_no_envia_nada(client, correos):
    crear_usuario('sin_correo')
    response = pedir_codigo(client, 'sin_correo')
    assert 'te enviamos'.encode() in response.data
    assert correos == []


def test_codigo_correcto_cambia_la_contrasena(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    response = verificar(client, correos[0]['codigo'])
    assert 'Tu contraseña se cambió'.encode() in response.data
    assert cuenta.check_password('nueva456')
    assert not cuenta.check_password('vieja123')
    assert CodigoRecuperacion.query.count() == 0  # se borra apenas se usa


def test_codigo_no_se_puede_reutilizar(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    codigo = correos[0]['codigo']
    verificar(client, codigo)
    response = verificar(client, codigo, nueva='otra789')
    assert cuenta.check_password('nueva456')
    assert 'Primero solicita un código'.encode() in response.data


def test_codigo_incorrecto_no_cambia_nada(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    incorrecto = '000000' if correos[0]['codigo'] != '000000' else '111111'
    response = verificar(client, incorrecto)
    assert 'incorrecto o ya venció'.encode() in response.data
    assert cuenta.check_password('vieja123')


def test_maximo_cinco_intentos(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    correcto = correos[0]['codigo']
    incorrecto = '000000' if correcto != '000000' else '111111'
    for _ in range(5):
        verificar(client, incorrecto)
    response = verificar(client, correcto)  # ya agotó los intentos
    assert 'incorrecto o ya venció'.encode() in response.data
    assert cuenta.check_password('vieja123')


def test_codigo_vencido_no_sirve(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    registro = CodigoRecuperacion.query.one()
    registro.expira = registro.creado - timedelta(minutes=1)
    db.session.commit()
    response = verificar(client, correos[0]['codigo'])
    assert 'incorrecto o ya venció'.encode() in response.data
    assert cuenta.check_password('vieja123')


def test_no_reenvia_codigos_muy_seguido(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    pedir_codigo(client, 'lulero')
    assert len(correos) == 1


def test_contrasenas_distintas_no_se_aceptan(client, cuenta, correos):
    pedir_codigo(client, 'lulero')
    response = verificar(client, correos[0]['codigo'], nueva='abc', confirmar='xyz')
    assert 'no coinciden'.encode() in response.data
    assert cuenta.check_password('vieja123')


def test_verificar_sin_haber_pedido_codigo(client, cuenta):
    response = verificar(client, '123456')
    assert 'Primero solicita un código'.encode() in response.data


def test_si_falla_el_envio_avisa(client, cuenta, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError('SMTP caído')
    monkeypatch.setattr(auth, 'enviar_codigo_recuperacion', falla)
    response = pedir_codigo(client, 'lulero')
    assert 'No pudimos enviar el correo'.encode() in response.data
    assert CodigoRecuperacion.query.count() == 0


def test_sin_configuracion_de_correo_lanza_error(app):
    from app.utils.correo import enviar_correo
    app.config['MAIL_USERNAME'] = ''
    with pytest.raises(RuntimeError):
        enviar_correo('a@b.com', 'asunto', 'texto')


def test_plantilla_del_correo_muestra_codigo_y_protege_el_nombre(app):
    from app.utils.correo import armar_correo_recuperacion
    with app.test_request_context():
        asunto, texto, html, imagenes = armar_correo_recuperacion('<b>pirata</b>', '482915', 15)
    assert '482915' in asunto and '482915' in texto and '482915' in html
    assert '15 minutos' in html
    assert '<b>pirata</b>' not in html and '&lt;b&gt;pirata&lt;/b&gt;' in html
    cid, ruta = imagenes[0]
    assert f'cid:{cid}' in html


def test_correo_se_envia_con_la_foto_incrustada(app, monkeypatch):
    import smtplib
    from app.utils import correo

    enviados = []

    class SMTPFalso:
        def __init__(self, servidor, puerto, timeout=None):
            self.datos = (servidor, puerto)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            pass
        def login(self, usuario, clave):
            self.login_con = (usuario, clave)
        def send_message(self, mensaje):
            enviados.append((self.datos, self.login_con, mensaje))

    monkeypatch.setattr(smtplib, 'SMTP', SMTPFalso)
    app.config.update(MAIL_SERVER='smtp.gmail.com', MAIL_PORT=587,
                      MAIL_USERNAME='app@ejemplo.com', MAIL_PASSWORD='clave-app', MAIL_SENDER='')
    with app.test_request_context():
        correo.enviar_codigo_recuperacion('destino@ejemplo.com', 'lulero', '123456', 15)

    (datos, login_con, mensaje), = enviados
    assert datos == ('smtp.gmail.com', 587)
    assert login_con == ('app@ejemplo.com', 'clave-app')
    assert mensaje['To'] == 'destino@ejemplo.com'
    assert '123456' in mensaje['Subject']
    tipos = [parte.get_content_type() for parte in mensaje.walk()]
    assert 'text/plain' in tipos and 'text/html' in tipos and 'image/jpeg' in tipos
