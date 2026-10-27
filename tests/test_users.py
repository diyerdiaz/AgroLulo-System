from app.models.users import User
from tests.conftest import iniciar_sesion


def test_registro_crea_cuenta_activa(client):
    response = client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'clave123'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'Cuenta creada exitosamente'.encode() in response.data
    nuevo = User.query.filter_by(nameUser='nuevo').first()
    assert nuevo is not None and nuevo.activo


def test_registro_rechaza_nombre_repetido(client, user):
    response = client.post('/User/add', data={'nameUser': 'test_user', 'passwordUser': 'x'})
    assert 'Ya existe una cuenta'.encode() in response.data
    assert User.query.filter_by(nameUser='test_user').count() == 1


def test_admin_ve_panel_de_usuarios(client, admin):
    iniciar_sesion(client, admin)
    assert client.get('/usuarios').status_code == 200
    assert client.get('/usuarios/estadisticas').status_code == 200
