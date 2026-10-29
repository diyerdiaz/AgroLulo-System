import os

import pytest

from app import db
from tests.conftest import crear_usuario, iniciar_sesion

STATIC = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')


def test_usuario_nuevo_no_ha_visto_el_recorrido(app):
    assert crear_usuario('nuevo').tutorial_visto is False


def test_usuario_nuevo_ve_a_don_pancho_al_entrar(logged_client):
    html = logged_client.get('/dashboard').data.decode()
    assert 'id="donPancho"' in html
    assert 'data-mostrar="1"' in html


def test_quien_ya_lo_vio_no_lo_ve_solo(logged_client, user):
    user.tutorial_visto = True
    db.session.commit()
    html = logged_client.get('/dashboard').data.decode()
    assert 'data-mostrar="0"' in html


def test_boton_de_ayuda_siempre_esta(logged_client, user):
    user.tutorial_visto = True
    db.session.commit()
    assert 'id="btnDonPancho"' in logged_client.get('/dashboard').data.decode()


def test_saltar_o_terminar_lo_marca_como_visto(logged_client, user):
    response = logged_client.post('/tutorial/visto')
    assert response.status_code == 204
    assert user.tutorial_visto is True
    assert 'data-mostrar="0"' in logged_client.get('/dashboard').data.decode()


def test_marcar_visto_exige_sesion(client):
    response = client.post('/tutorial/visto')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_marcar_visto_solo_afecta_a_la_propia_cuenta(client, app):
    uno = crear_usuario('uno')
    otro = crear_usuario('otro')
    iniciar_sesion(client, uno)
    client.post('/tutorial/visto')
    assert uno.tutorial_visto is True
    assert otro.tutorial_visto is False


@pytest.mark.parametrize('paso', ['menu', 'cultivos', 'calendario', 'gastos',
                                  'ingresos', 'pagos', 'resumen', 'perfil', 'ayuda'])
def test_cada_paso_tiene_donde_senalar(logged_client, paso):
    assert f'data-tour="{paso}"' in logged_client.get('/dashboard').data.decode()


@pytest.mark.parametrize('archivo', ['img/don-pancho/saludando.webp', 'img/don-pancho/senalando.webp',
                                     'img/don-pancho/pensando.webp', 'img/don-pancho/cara.webp',
                                     'js/don-pancho.js'])
def test_archivos_de_don_pancho_existen(client, archivo):
    assert os.path.isfile(os.path.join(STATIC, archivo))
    assert client.get('/static/' + archivo).status_code == 200
