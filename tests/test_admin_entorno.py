import pytest

from app import create_app, db
from app.models.users import User

CLAVE = 'ClaveDeLaFinca2026'


@pytest.fixture
def config(tmp_path):
    return {
        'TESTING': True,
        'SECRET_KEY': 'x',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/a.sqlite',
        'ADMIN_USUARIO': 'jefe',
        'ADMIN_CORREO': 'Jefe@Ejemplo.com',
        'ADMIN_PASSWORD': CLAVE,
    }


def _admin(app):
    with app.app_context():
        cuenta = User.query.filter_by(isAdmin=True).one()
        db.session.expunge(cuenta)
        return cuenta


def test_el_primer_arranque_crea_el_admin_con_las_variables(config):
    admin = _admin(create_app(config))
    assert admin.nameUser == 'jefe'
    assert admin.emailUser == 'jefe@ejemplo.com'
    assert admin.check_password(CLAVE)
    assert admin.debe_cambiar_password is False


def test_el_admin_puede_iniciar_sesion(config):
    app = create_app({**config, 'WTF_CSRF_ENABLED': False})
    respuesta = app.test_client().post('/login', data={'nameUser': 'jefe', 'passwordUser': CLAVE})
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/dashboard')


def test_un_nuevo_despliegue_no_cambia_la_contrasena_de_la_pagina(config):
    app = create_app(config)
    with app.app_context():
        User.query.filter_by(isAdmin=True).one().set_password('OtraClave2027')
        db.session.commit()

    admin = _admin(create_app(config))
    assert admin.check_password('OtraClave2027')


def test_sin_variables_sigue_con_contrasena_aleatoria(config):
    config.update(ADMIN_USUARIO='', ADMIN_CORREO='', ADMIN_PASSWORD='')
    admin = _admin(create_app(config))
    assert admin.nameUser == 'admin'
    assert admin.debe_cambiar_password is True


def test_una_contrasena_debil_no_se_aplica(config, capsys):
    config['ADMIN_PASSWORD'] = 'debil'
    admin = _admin(create_app(config))
    assert admin.debe_cambiar_password is True
    assert not admin.check_password('debil')
    assert 'ADMIN_PASSWORD no se aplicó' in capsys.readouterr().out


def test_configura_una_cuenta_que_seguia_pendiente(config):
    sin_clave = {**config, 'ADMIN_USUARIO': '', 'ADMIN_CORREO': '', 'ADMIN_PASSWORD': ''}
    create_app(sin_clave)
    admin = _admin(create_app(config))
    assert admin.nameUser == 'jefe'
    assert admin.check_password(CLAVE)
