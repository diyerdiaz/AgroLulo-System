from app.models.users import User
from tests.conftest import iniciar_sesion, crear_usuario


def test_registro_crea_cuenta_activa(client):
    response = client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'Lulo2026x',
                                              'emailUser': 'Nuevo@Ejemplo.com'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'Cuenta creada exitosamente'.encode() in response.data
    nuevo = User.query.filter_by(nameUser='nuevo').first()
    assert nuevo is not None and nuevo.activo
    assert nuevo.emailUser == 'nuevo@ejemplo.com'  # se guarda en minúsculas


def test_registro_exige_correo_valido(client):
    response = client.post('/User/add', data={'nameUser': 'sin_correo', 'passwordUser': 'x',
                                              'emailUser': 'no-es-correo'})
    assert 'correo electrónico válido'.encode() in response.data
    assert User.query.filter_by(nameUser='sin_correo').first() is None


def test_registro_rechaza_correo_repetido(client):
    crear_usuario('dueno', correo='dueno@ejemplo.com')
    response = client.post('/User/add', data={'nameUser': 'otro', 'passwordUser': 'x',
                                              'emailUser': 'DUENO@ejemplo.com'})
    assert 'Ese correo ya está registrado'.encode() in response.data
    assert User.query.filter_by(nameUser='otro').first() is None


def test_perfil_permite_agregar_correo(logged_client, user):
    logged_client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'test_user',
                                        'emailUser': 'mio@ejemplo.com'})
    assert user.emailUser == 'mio@ejemplo.com'


def test_perfil_rechaza_correo_de_otra_cuenta(logged_client, user):
    crear_usuario('otro', correo='ocupado@ejemplo.com')
    logged_client.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'test_user',
                                        'emailUser': 'ocupado@ejemplo.com'})
    assert user.emailUser is None


def test_registro_rechaza_nombre_repetido(client, user):
    response = client.post('/User/add', data={'nameUser': 'test_user', 'passwordUser': 'x',
                                              'emailUser': 'repetido@ejemplo.com'})
    assert 'Ya existe una cuenta'.encode() in response.data
    assert User.query.filter_by(nameUser='test_user').count() == 1


def test_admin_ve_panel_de_usuarios(client, admin):
    iniciar_sesion(client, admin)
    assert client.get('/usuarios').status_code == 200
    assert client.get('/usuarios/estadisticas').status_code == 200
