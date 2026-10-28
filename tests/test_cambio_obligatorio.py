from sqlalchemy import text

from app import db, _asegurar_columnas
from app.models.users import User
from tests.conftest import crear_usuario, iniciar_sesion


def cuenta_vieja(nombre='viejo', clave='clave123', correo=None):
    """Cuenta creada antes de las reglas de seguridad (queda marcada)."""
    user = crear_usuario(nombre, clave=clave, correo=correo)
    user.debe_cambiar_password = True
    db.session.commit()
    return user


def entrar(client, nombre, clave):
    return client.post('/', data={'nameUser': nombre, 'passwordUser': clave})


def cambiar(client, nueva='Lulo2026x', confirmar=None, correo=None):
    datos = {'nueva_password': nueva, 'confirmar_password': nueva if confirmar is None else confirmar}
    if correo is not None:
        datos['emailUser'] = correo
    return client.post('/cambiar-contrasena', data=datos, follow_redirects=True)


def test_migracion_marca_las_cuentas_que_ya_existian(app):
    db.session.execute(text('CREATE TABLE cuentas_viejas (id INTEGER PRIMARY KEY)'))
    db.session.execute(text('INSERT INTO cuentas_viejas (id) VALUES (1), (2)'))
    db.session.commit()
    _asegurar_columnas('cuentas_viejas', [('debe_cambiar_password', 'BOOLEAN NOT NULL DEFAULT 1')])
    valores = db.session.execute(text('SELECT debe_cambiar_password FROM cuentas_viejas')).scalars().all()
    assert valores == [1, 1]


def test_admin_sembrado_debe_cambiar_su_contrasena(app):
    assert User.query.filter_by(nameUser='admin').one().debe_cambiar_password


def test_cuentas_nuevas_no_quedan_marcadas(client):
    client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'Lulo2026x',
                                   'emailUser': 'nuevo@ejemplo.com'})
    assert not User.query.filter_by(nameUser='nuevo').one().debe_cambiar_password


def test_cuenta_vieja_es_llevada_a_cambiar_al_entrar(client):
    cuenta_vieja()
    response = entrar(client, 'viejo', 'clave123')
    assert response.headers['Location'].endswith('/cambiar-contrasena')


def test_cuenta_vieja_no_puede_usar_otras_paginas(client):
    iniciar_sesion(client, cuenta_vieja())
    for url in ['/dashboard', '/cultivos/', '/gastos/', '/perfil', '/usuarios']:
        response = client.get(url)
        assert response.status_code == 302, url
        assert response.headers['Location'].endswith('/cambiar-contrasena'), url
    assert client.get('/cambiar-contrasena').status_code == 200


def test_cuenta_vieja_si_puede_cerrar_sesion(client):
    iniciar_sesion(client, cuenta_vieja())
    response = client.get('/logout')
    assert not response.headers['Location'].endswith('/cambiar-contrasena')


def test_contrasena_debil_al_entrar_tambien_obliga_a_cambiarla(client):
    user = crear_usuario('debil', clave='clave123')  # sin marca, pero no cumple las reglas
    response = entrar(client, 'debil', 'clave123')
    assert response.headers['Location'].endswith('/cambiar-contrasena')
    assert user.debe_cambiar_password


def test_contrasena_segura_entra_normal(client):
    crear_usuario('segura', clave='Lulo2026x')
    response = entrar(client, 'segura', 'Lulo2026x')
    assert response.headers['Location'].endswith('/dashboard')


def test_cambio_exitoso_guarda_correo_y_libera_la_cuenta(client):
    user = cuenta_vieja()
    iniciar_sesion(client, user)
    response = cambiar(client, correo='Viejo@Ejemplo.com')
    assert 'Tu contraseña se actualizó'.encode() in response.data
    assert user.check_password('Lulo2026x')
    assert user.emailUser == 'viejo@ejemplo.com'
    assert not user.debe_cambiar_password
    assert client.get('/dashboard').status_code == 200


def test_cuenta_con_correo_no_tiene_que_escribirlo(client):
    user = cuenta_vieja(correo='ya@ejemplo.com')
    iniciar_sesion(client, user)
    assert b'name="emailUser"' not in client.get('/cambiar-contrasena').data
    cambiar(client)
    assert not user.debe_cambiar_password and user.emailUser == 'ya@ejemplo.com'


def test_cambio_rechaza_contrasena_debil(client):
    user = cuenta_vieja()
    iniciar_sesion(client, user)
    response = cambiar(client, nueva='corta1', correo='viejo@ejemplo.com')
    assert 'La contraseña debe'.encode() in response.data
    assert user.debe_cambiar_password and user.check_password('clave123')


def test_cambio_rechaza_la_misma_contrasena(client):
    user = cuenta_vieja(clave='Lulo2026x')
    iniciar_sesion(client, user)
    response = cambiar(client, nueva='Lulo2026x', correo='viejo@ejemplo.com')
    assert 'distinta a la anterior'.encode() in response.data
    assert user.debe_cambiar_password


def test_cambio_exige_correo_si_la_cuenta_no_tiene(client):
    user = cuenta_vieja()
    iniciar_sesion(client, user)
    response = cambiar(client, correo='')
    assert 'correo electrónico válido'.encode() in response.data
    assert user.debe_cambiar_password


def test_cambio_rechaza_correo_de_otra_cuenta(client):
    crear_usuario('otro', correo='ocupado@ejemplo.com')
    user = cuenta_vieja()
    iniciar_sesion(client, user)
    response = cambiar(client, correo='ocupado@ejemplo.com')
    assert 'ya está registrado'.encode() in response.data
    assert user.debe_cambiar_password


def test_cambio_rechaza_confirmacion_distinta(client):
    user = cuenta_vieja()
    iniciar_sesion(client, user)
    response = cambiar(client, confirmar='Otra2026x', correo='viejo@ejemplo.com')
    assert 'no coinciden'.encode() in response.data
    assert user.debe_cambiar_password


def test_cuenta_sin_marca_no_ve_la_pantalla_de_cambio(logged_client):
    response = logged_client.get('/cambiar-contrasena')
    assert response.headers['Location'].endswith('/dashboard')
