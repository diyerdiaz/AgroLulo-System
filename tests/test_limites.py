from datetime import timedelta

from app import db
from app.models.intento_acceso import IntentoAcceso
from app.models.users import User
from app.utils.seguridad import LIMITES, _ahora, registrar_intento, segundos_bloqueo_restante
from tests.conftest import crear_usuario

CLAVE = 'ClaveFuerte123'


def _fallar_login(client, veces):
    for _ in range(veces):
        client.post('/login', data={'nameUser': 'test_user', 'passwordUser': 'mala'})


def test_el_bloqueo_sobrevive_a_un_reinicio_del_servidor(app, client, user):
    _fallar_login(client, LIMITES['login'][0])
    # Un cliente nuevo y la sesión limpia: solo queda lo guardado en la base de datos.
    db.session.remove()
    respuesta = app.test_client().post('/login', data={'nameUser': 'test_user', 'passwordUser': 'clave123'})
    assert 'Demasiados intentos'.encode() in respuesta.data


def test_el_bloqueo_vence_solo(client, user):
    _fallar_login(client, LIMITES['login'][0])
    for intento in IntentoAcceso.query.all():
        intento.fecha = _ahora() - timedelta(seconds=LIMITES['login'][1] + 1)
    db.session.commit()
    assert client.post('/login', data={'nameUser': 'test_user', 'passwordUser': 'clave123'}).status_code == 302


def test_el_login_correcto_borra_los_fallos(client, user):
    _fallar_login(client, LIMITES['login'][0] - 1)
    client.post('/login', data={'nameUser': 'test_user', 'passwordUser': 'clave123'})
    assert IntentoAcceso.query.filter_by(accion='login').count() == 0


def test_el_bloqueo_de_una_ip_no_afecta_a_otra(app, user):
    for _ in range(LIMITES['login'][0]):
        registrar_intento('203.0.113.1')
    assert segundos_bloqueo_restante('203.0.113.1') > 0
    assert segundos_bloqueo_restante('203.0.113.2') == 0


def test_los_intentos_viejos_se_borran_solos(app):
    db.session.add(IntentoAcceso(accion='login', clave='vieja', fecha=_ahora() - timedelta(days=3)))
    db.session.commit()
    registrar_intento('nueva')
    assert IntentoAcceso.query.filter_by(clave='vieja').count() == 0


def _registrar(client, numero):
    return client.post('/User/add', data={'nameUser': f'bot{numero}', 'passwordUser': CLAVE,
                                          'emailUser': f'bot{numero}@ejemplo.com'})


def test_limite_de_cuentas_nuevas_por_conexion(client):
    maximo = LIMITES['registro'][0]
    for numero in range(maximo):
        assert _registrar(client, numero).status_code == 302
    respuesta = _registrar(client, maximo)
    assert 'demasiadas cuentas'.encode() in respuesta.data
    assert User.query.filter_by(nameUser=f'bot{maximo}').first() is None


def test_un_registro_rechazado_no_gasta_el_cupo(client):
    crear_usuario('ya_existe')
    client.post('/User/add', data={'nameUser': 'ya_existe', 'passwordUser': CLAVE, 'emailUser': 'a@b.co'})
    assert IntentoAcceso.query.filter_by(accion='registro').count() == 0
