import pytest

from app.utils import seguridad

BOT = {'REMOTE_ADDR': '8.8.4.4'}
PERSONA = {'REMOTE_ADDR': '1.0.0.1'}


@pytest.fixture
def proxy(app):
    app.config['DETRAS_DE_HTTPS'] = True
    seguridad._visitas_recientes.clear()


def _probar(client, ruta, entorno=BOT, **kwargs):
    return client.get(ruta, environ_base=entorno, **kwargs)


def test_tres_rutas_trampa_bloquean_la_ip(client, proxy):
    for ruta in ('/wp-login.php', '/.env', '/phpmyadmin/'):
        assert _probar(client, ruta).status_code == 404
    assert _probar(client, '/login').status_code == 403


def test_una_ruta_trampa_sola_no_bloquea(client, proxy):
    _probar(client, '/wp-login.php')
    assert _probar(client, '/login').status_code == 200


def test_el_bloqueo_de_una_ip_no_afecta_a_otra(client, proxy):
    for ruta in ('/wp-login.php', '/.env', '/phpmyadmin/'):
        _probar(client, ruta)
    assert _probar(client, '/login', entorno=PERSONA).status_code == 200


def test_un_programa_de_ataque_queda_bloqueado_de_una(client, proxy):
    assert _probar(client, '/', headers={'User-Agent': 'sqlmap/1.8'}).status_code == 403
    assert _probar(client, '/').status_code == 403


def test_un_navegador_normal_pasa(client, proxy):
    chrome = 'Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile Safari/537.36'
    assert _probar(client, '/login', headers={'User-Agent': chrome}).status_code == 200


def test_demasiadas_visitas_bloquean_la_ip(client, proxy, monkeypatch):
    monkeypatch.setattr(seguridad, 'PETICIONES_POR_MINUTO', 3)
    estados = [_probar(client, '/login').status_code for _ in range(5)]
    assert estados == [200, 200, 200, 403, 403]


def test_los_archivos_estaticos_no_cuentan(client, proxy, monkeypatch):
    monkeypatch.setattr(seguridad, 'PETICIONES_POR_MINUTO', 3)
    for _ in range(6):
        assert _probar(client, '/static/css/style.css').status_code == 200
    assert _probar(client, '/login').status_code == 200


def test_un_post_de_una_ip_bloqueada_se_corta_antes_de_todo(client, proxy):
    _probar(client, '/', headers={'User-Agent': 'nikto'})
    respuesta = client.post('/login', data={'nameUser': 'x', 'passwordUser': 'y'}, environ_base=BOT)
    assert respuesta.status_code == 403


def test_nunca_se_bloquea_sin_proxy(client):
    for ruta in ('/wp-login.php', '/.env', '/phpmyadmin/', '/xmlrpc.php'):
        _probar(client, ruta)
    assert _probar(client, '/login').status_code == 200


@pytest.mark.parametrize('interna', ['127.0.0.1', '10.0.1.5', '172.18.0.3'])
def test_nunca_se_bloquea_una_ip_interna(client, proxy, interna):
    entorno = {'REMOTE_ADDR': interna}
    for ruta in ('/wp-login.php', '/.env', '/phpmyadmin/', '/xmlrpc.php'):
        _probar(client, ruta, entorno=entorno)
    assert _probar(client, '/login', entorno=entorno).status_code == 200


def test_el_comando_desbloquea_la_ip(app, client, proxy):
    _probar(client, '/', headers={'User-Agent': 'nikto'})
    assert _probar(client, '/login').status_code == 403
    resultado = app.test_cli_runner().invoke(args=['desbloquear-ip', BOT['REMOTE_ADDR']])
    assert 'ya no está bloqueada' in resultado.output
    assert _probar(client, '/login').status_code == 200


@pytest.mark.parametrize('ruta', ['/', '/login', '/User/add', '/offline', '/sw.js', '/cultivos/', '/dashboard'])
def test_las_paginas_reales_no_son_trampas(ruta):
    assert seguridad._RUTAS_TRAMPA.search(ruta) is None
