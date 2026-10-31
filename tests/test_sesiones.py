from flask import g

from tests.conftest import iniciar_sesion

CLAVE_NUEVA = 'ClaveNueva456'


def _cambiar_clave(cliente, user, clave_actual='clave123'):
    return cliente.post('/perfil', data={
        'password_actual': clave_actual, 'nameUser': user.nameUser, 'emailUser': '',
        'nueva_password': CLAVE_NUEVA, 'confirmar_password': CLAVE_NUEVA,
    })


def test_cambiar_la_clave_cierra_las_otras_sesiones(app, user):
    mia, ajena = app.test_client(), app.test_client()
    iniciar_sesion(mia, user)
    iniciar_sesion(ajena, user)
    assert ajena.get('/perfil').status_code == 200

    _cambiar_clave(mia, user)

    assert mia.get('/perfil').status_code == 200
    # El fixture app deja abierto un contexto: sin esto, Flask-Login reusaría
    # el usuario de la petición anterior en vez de leer la cookie de "ajena".
    g.pop('_login_user', None)
    respuesta = ajena.get('/perfil')
    assert respuesta.status_code == 302
    assert '/login' in respuesta.headers['Location']


def test_una_sesion_con_el_formato_anterior_ya_no_sirve(client, user):
    with client.session_transaction() as s:
        s['_user_id'] = str(user.idUser)
        s['_fresh'] = True
    assert client.get('/perfil').status_code == 302


def test_cambiar_el_nombre_no_cierra_la_sesion(app, user):
    cliente = app.test_client()
    iniciar_sesion(cliente, user)
    cliente.post('/perfil', data={'password_actual': 'clave123', 'nameUser': 'otro_nombre', 'emailUser': ''})
    assert cliente.get('/perfil').status_code == 200
