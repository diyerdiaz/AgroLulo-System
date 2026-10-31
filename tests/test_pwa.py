import json
import pathlib

from tests.conftest import crear_usuario, iniciar_sesion

SW = pathlib.Path(__file__).parent.parent / 'app' / 'static' / 'js' / 'sw.js'


def test_el_manifest_cumple_lo_que_chrome_pide_para_instalar(client):
    respuesta = client.get('/static/manifest.webmanifest')
    assert respuesta.status_code == 200
    assert 'manifest+json' in respuesta.content_type
    manifest = json.loads(respuesta.data)
    assert manifest['display'] == 'standalone'
    assert manifest['start_url'] == '/login'
    assert {'192x192', '512x512'} <= {i['sizes'] for i in manifest['icons']}
    for icono in manifest['icons']:
        assert client.get(icono['src']).status_code == 200


def test_el_service_worker_se_sirve_desde_la_raiz(client):
    respuesta = client.get('/sw.js')
    assert respuesta.status_code == 200
    assert 'javascript' in respuesta.content_type
    assert respuesta.headers['Cache-Control'] == 'no-cache'


def test_las_paginas_enlazan_el_manifest_y_el_boton(client):
    for url in ('/', '/login'):
        html = client.get(url).get_data(as_text=True)
        assert 'rel="manifest"' in html
        assert 'data-instalar-boton' in html
        assert 'js/instalar-app.js' in html


def test_la_pantalla_sin_conexion_no_lleva_datos_de_la_sesion(logged_client):
    html = logged_client.get('/offline').get_data(as_text=True)
    assert 'csrf' not in html
    assert 'test_user' not in html


def test_el_service_worker_no_guarda_paginas_privadas():
    codigo = SW.read_text(encoding='utf-8')
    assert 'cache.put' not in codigo
    for privada in ('/dashboard', '/cultivos', '/gastos', '/ingresos', '/pagos', '/perfil', '/usuarios'):
        assert privada not in codigo


def test_se_abre_aunque_la_cuenta_deba_cambiar_su_contrasena(client, app):
    cuenta = crear_usuario('obligada')
    cuenta.debe_cambiar_password = True
    iniciar_sesion(client, cuenta)
    assert client.get('/offline').status_code == 200
    assert client.get('/sw.js').status_code == 200
