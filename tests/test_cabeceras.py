from app import create_app


def test_las_paginas_traen_las_cabeceras_de_seguridad(client):
    cabeceras = client.get('/login').headers
    assert "frame-ancestors 'none'" in cabeceras['Content-Security-Policy']
    assert cabeceras['X-Frame-Options'] == 'DENY'
    assert cabeceras['X-Content-Type-Options'] == 'nosniff'
    assert cabeceras['Referrer-Policy'] == 'strict-origin-when-cross-origin'


def test_sin_https_no_se_exige_https(client):
    assert 'Strict-Transport-Security' not in client.get('/login').headers


def test_la_cookie_de_sesion_es_httponly_y_samesite(client):
    cookie = client.get('/login').headers['Set-Cookie']
    assert 'HttpOnly' in cookie
    assert 'SameSite=Lax' in cookie
    assert 'Secure' not in cookie


def test_detras_de_https_activa_cookie_segura_hsts_e_ip_real():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'clave-de-pruebas',
        'DETRAS_DE_HTTPS': True,
        'SESSION_COOKIE_SECURE': True,
    })
    client = app.test_client()
    respuesta = client.get('/login', headers={'X-Forwarded-Proto': 'https'})
    assert respuesta.headers['Strict-Transport-Security'] == 'max-age=31536000'
    assert 'Secure' in respuesta.headers['Set-Cookie']

    with app.test_request_context('/', headers={'X-Forwarded-For': '203.0.113.9'},
                                  environ_base={'REMOTE_ADDR': '10.0.0.1'}):
        from flask import request
        environ = dict(request.environ)
    capturado = {}

    def app_final(entorno, iniciar):
        capturado['ip'] = entorno['REMOTE_ADDR']
        return []

    app.wsgi_app.app = app_final
    app.wsgi_app(environ, lambda *a: None)
    assert capturado['ip'] == '203.0.113.9'


def test_las_paginas_privadas_no_se_guardan_en_el_navegador(logged_client):
    assert logged_client.get('/perfil').headers['Cache-Control'] == 'no-store'


def test_los_archivos_estaticos_si_se_pueden_guardar(logged_client):
    respuesta = logged_client.get('/static/css/style.css')
    assert respuesta.headers.get('Cache-Control') != 'no-store'


def test_un_texto_enorme_no_se_guarda(logged_client, user):
    from app.models.actividad import ActividadCultivo
    from tests.conftest import crear_cultivo
    cultivo = crear_cultivo(user)
    respuesta = logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad', data={
        'tipo': 'otro', 'fecha': '2026-01-15', 'nota': 'x' * 40000,
    })
    assert respuesta.status_code == 413
    assert ActividadCultivo.query.count() == 0
    logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad', data={
        'tipo': 'otro', 'fecha': '2026-01-15', 'nota': 'x' * 1000,
    })
    assert ActividadCultivo.query.count() == 1
