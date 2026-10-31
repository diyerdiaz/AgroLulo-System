import pathlib
import re

import pytest

from app.models.cultivo import Cultivo
from tests.conftest import iniciar_sesion

PLANTILLAS = pathlib.Path(__file__).parent.parent / 'app' / 'templates'
DATOS_CULTIVO = {'nombre': 'Lote CSRF', 'hectareas': '1', 'fecha_sembrado': '2026-01-15'}


@pytest.fixture
def csrf_activo(app):
    app.config['WTF_CSRF_ENABLED'] = True


def _token_de(respuesta):
    return re.search(r'name="csrf-token" content="([^"]+)"', respuesta.get_data(as_text=True)).group(1)


def test_todos_los_formularios_post_llevan_el_token():
    faltan = []
    for archivo in PLANTILLAS.rglob('*.html'):
        for formulario in re.findall(r'<form\b.*?</form>', archivo.read_text(encoding='utf-8'), re.S | re.I):
            if re.search(r'method\s*=\s*["\']post["\']', formulario, re.I) and 'csrf_token()' not in formulario:
                faltan.append(archivo.name)
    assert faltan == []


def test_post_sin_token_se_rechaza(client, user, csrf_activo):
    iniciar_sesion(client, user)
    respuesta = client.post('/cultivos/add', data=DATOS_CULTIVO)
    assert respuesta.status_code == 302
    assert '/login' in respuesta.headers['Location']
    assert Cultivo.query.filter_by(nombre='Lote CSRF').first() is None


def test_post_con_token_se_acepta(client, user, csrf_activo):
    iniciar_sesion(client, user)
    token = _token_de(client.get('/cultivos/new'))
    client.post('/cultivos/add', data={**DATOS_CULTIVO, 'csrf_token': token})
    assert Cultivo.query.filter_by(nombre='Lote CSRF').first() is not None


def test_el_javascript_puede_enviar_el_token_en_la_cabecera(client, user, csrf_activo):
    iniciar_sesion(client, user)
    token = _token_de(client.get('/cultivos/new'))
    respuesta = client.post('/tutorial/visto', headers={'X-CSRFToken': token})
    assert respuesta.status_code == 204


def test_el_token_de_otra_sesion_no_sirve(app, user, csrf_activo):
    atacante = app.test_client()
    token_ajeno = _token_de(atacante.get('/login'))

    victima = app.test_client()
    iniciar_sesion(victima, user)
    victima.post('/cultivos/add', data={**DATOS_CULTIVO, 'csrf_token': token_ajeno})
    assert Cultivo.query.filter_by(nombre='Lote CSRF').first() is None
