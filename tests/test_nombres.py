import pytest

from app import create_app, db
from app.models.users import User
from app.utils.seguridad import error_nombre_usuario

CLAVE = 'ClaveFuerte123'


@pytest.mark.parametrize('nombre', ['', 'ab', 'x' * 31, 'uno\ndos', 'correo@falso.co', "x'+alert(1)+'",
                                    'admin', 'Admin', 'ADMINISTRADOR', 'root'])
def test_nombres_rechazados(nombre):
    assert error_nombre_usuario(nombre)


@pytest.mark.parametrize('nombre', ['lulero', 'Don Pancho', 'José_Peña', 'finca.el-lulo'])
def test_nombres_aceptados(nombre):
    assert error_nombre_usuario(nombre) is None


def test_el_registro_rechaza_nombre_vacio(client):
    client.post('/User/add', data={'nameUser': '   ', 'passwordUser': CLAVE, 'emailUser': 'a@ejemplo.com'})
    assert User.query.filter_by(emailUser='a@ejemplo.com').first() is None


def test_nadie_puede_cambiarse_el_nombre_a_admin(logged_client, user):
    logged_client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'Admin', 'emailUser': ''})
    assert db.session.get(User, user.idUser).nameUser == 'test_user'


def test_una_cuenta_vieja_puede_conservar_su_nombre(app, client):
    from tests.conftest import crear_usuario, iniciar_sesion
    vieja = crear_usuario('ab')
    iniciar_sesion(client, vieja)
    client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'ab', 'emailUser': 'ab@ejemplo.com'})
    assert db.session.get(User, vieja.idUser).emailUser == 'ab@ejemplo.com'


def test_llamarse_admin_no_da_permisos_al_reiniciar(tmp_path):
    config = {'TESTING': True, 'SECRET_KEY': 'x', 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/a.sqlite'}
    app = create_app(config)
    with app.app_context():
        jefe = User.query.filter_by(nameUser='admin').one()
        jefe.nameUser = 'gerente'
        intruso = User(nameUser='admin', activo=True)
        intruso.set_password(CLAVE)
        db.session.add(intruso)
        db.session.commit()

    app = create_app(config)
    with app.app_context():
        assert User.query.filter_by(nameUser='admin').one().isAdmin is False
        assert User.query.filter_by(nameUser='gerente').one().isAdmin is True
        assert User.query.count() == 2
