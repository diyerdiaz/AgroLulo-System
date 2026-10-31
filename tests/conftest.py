import pytest
from datetime import date

from app import create_app, db


@pytest.fixture
def app():
    # Base de datos en memoria: los tests NUNCA tocan instance/flaskdb.sqlite.
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'clave-de-pruebas',
        # Los tests envían formularios directo, sin cargar antes la página.
        # La protección se prueba aparte en tests/test_csrf.py.
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def crear_usuario(nombre, clave='clave123', activo=True, admin=False, correo=None):
    from app.models.users import User
    user = User(nameUser=nombre, emailUser=correo, activo=activo, isAdmin=admin)
    user.set_password(clave)
    db.session.add(user)
    db.session.commit()
    return user


def crear_cultivo(user, nombre='Lote de prueba'):
    from app.models.cultivo import Cultivo
    cultivo = Cultivo(idUser=user.idUser, nombre=nombre, hectareas=1.0,
                      plantas=680, fecha_sembrado=date(2026, 1, 15))
    db.session.add(cultivo)
    db.session.commit()
    return cultivo


def iniciar_sesion(client, user):
    with client.session_transaction() as s:
        s['_user_id'] = user.get_id()
        s['_fresh'] = True


@pytest.fixture
def user(app):
    return crear_usuario('test_user')


@pytest.fixture
def admin(app):
    from app.models.users import User
    admin = User.query.filter_by(nameUser='admin').first()
    # El admin sembrado nace obligado a cambiar su contraseña; para
    # los tests que lo usan como administrador normal se quita esa marca.
    admin.debe_cambiar_password = False
    db.session.commit()
    return admin


@pytest.fixture
def logged_client(client, user):
    iniciar_sesion(client, user)
    return client
