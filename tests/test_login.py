from app.models.users import User
from tests.conftest import crear_usuario


def test_pagina_login_carga(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Iniciar'.encode() in response.data


def test_login_exitoso_redirige_al_dashboard(client):
    crear_usuario('segura', clave='Lulo2026x')
    response = client.post('/', data={'nameUser': 'segura', 'passwordUser': 'Lulo2026x'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_login_credenciales_invalidas(client, user):
    response = client.post('/', data={'nameUser': 'test_user', 'passwordUser': 'otra'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'Credenciales inválidas'.encode() in response.data


def test_cuenta_bloqueada_no_puede_entrar(client):
    crear_usuario('bloqueado', activo=False)
    response = client.post('/', data={'nameUser': 'bloqueado', 'passwordUser': 'clave123'},
                           follow_redirects=True)
    assert 'esperando a que el administrador la active'.encode() in response.data


def test_bloqueo_tras_muchos_intentos_fallidos(client, user):
    for _ in range(5):
        client.post('/', data={'nameUser': 'test_user', 'passwordUser': 'mal'})
    response = client.post('/', data={'nameUser': 'test_user', 'passwordUser': 'clave123'})
    assert 'Demasiados intentos fallidos'.encode() in response.data


def test_dashboard_requiere_sesion(client):
    response = client.get('/dashboard')
    assert response.status_code == 302


def test_logout_cierra_sesion(logged_client):
    logged_client.get('/logout')
    assert logged_client.get('/dashboard').status_code == 302


def test_admin_se_crea_al_arrancar(admin):
    assert admin is not None
    assert admin.isAdmin and admin.activo


def test_contrasenas_se_guardan_encriptadas(user):
    assert user.passwordUser != 'clave123'
    assert User.es_hash_valido(user.passwordUser)
