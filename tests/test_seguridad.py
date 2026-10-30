import pytest

from app.models.users import User
from app.utils.seguridad import errores_contrasena, mensaje_contrasena_invalida
from tests.conftest import iniciar_sesion


def test_contrasena_fuerte_no_tiene_errores():
    assert errores_contrasena('Lulo2026x', 'lulero') == []


@pytest.mark.parametrize('contrasena, regla', [
    ('Ab1', 'al menos 8 caracteres'),
    ('lulo2026x', 'mayúscula'),
    ('LULO2026X', 'minúscula'),
    ('LuloLuloLulo', 'número'),
    ('Lulero2026', 'nombre de usuario'),
    ('A1' + 'b' * 130, 'máximo 128'),
])
def test_cada_regla_se_detecta(contrasena, regla):
    errores = errores_contrasena(contrasena, 'lulero')
    assert any(regla in e for e in errores), errores


def test_acepta_tildes_y_enie():
    assert errores_contrasena('Ñandú2026', 'pepe') == []


def test_mensaje_une_todas_las_reglas():
    mensaje = mensaje_contrasena_invalida(['tener al menos un número', 'tener al menos una letra mayúscula'])
    assert mensaje == 'La contraseña debe tener al menos un número y tener al menos una letra mayúscula.'


def test_registro_rechaza_contrasena_debil(client):
    response = client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'clave123',
                                              'emailUser': 'nuevo@ejemplo.com'})
    assert 'La contraseña debe'.encode() in response.data
    assert User.query.filter_by(nameUser='nuevo').first() is None


def test_registro_exige_correo(client):
    response = client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'Lulo2026x',
                                              'emailUser': ''})
    assert 'correo electrónico válido'.encode() in response.data
    assert User.query.filter_by(nameUser='nuevo').first() is None


def test_perfil_rechaza_contrasena_debil(logged_client, user):
    logged_client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'test_user',
                                        'nueva_password': 'corta', 'confirmar_password': 'corta'})
    assert user.check_password('clave123')


def test_perfil_acepta_contrasena_fuerte(logged_client, user):
    logged_client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'test_user',
                                        'nueva_password': 'Lulo2026x', 'confirmar_password': 'Lulo2026x'})
    assert user.check_password('Lulo2026x')


def test_admin_crea_cuenta_con_correo_y_contrasena_fuerte(client, admin):
    iniciar_sesion(client, admin)
    client.post('/usuarios/crear', data={'nameUser': 'trabajador', 'passwordUser': 'Lulo2026x',
                                         'emailUser': 'trabajador@ejemplo.com'})
    nuevo = User.query.filter_by(nameUser='trabajador').first()
    assert nuevo is not None and nuevo.emailUser == 'trabajador@ejemplo.com'


@pytest.mark.parametrize('datos', [
    {'nameUser': 'trabajador', 'passwordUser': 'Lulo2026x', 'emailUser': ''},
    {'nameUser': 'trabajador', 'passwordUser': 'debil', 'emailUser': 'trabajador@ejemplo.com'},
])
def test_admin_no_crea_cuenta_sin_correo_o_con_contrasena_debil(client, admin, datos):
    iniciar_sesion(client, admin)
    client.post('/usuarios/crear', data=datos)
    assert User.query.filter_by(nameUser='trabajador').first() is None


# --- Lo que un atacante podría aprovechar ---

def test_admin_nuevo_no_tiene_la_contrasena_123(app):
    from app.models.users import User
    admin = User.query.filter_by(nameUser='admin').one()
    for adivinanza in ['123', 'admin', '1234', 'password', '']:
        assert not admin.check_password(adivinanza)


def test_errores_no_muestran_detalles_internos(app):
    @app.route('/_prueba_error')
    def _prueba_error():
        raise RuntimeError('detalle secreto: tabla users, ruta /home/servidor')

    respuesta = app.test_client().get('/_prueba_error')
    assert respuesta.status_code == 500
    assert b'detalle secreto' not in respuesta.data and b'/home/' not in respuesta.data


def test_pagina_inexistente_responde_404_sin_detalles(client):
    respuesta = client.get('/esta-pagina-no-existe')
    assert respuesta.status_code == 404
