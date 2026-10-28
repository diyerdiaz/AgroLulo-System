from tests.conftest import crear_usuario


def test_landing_es_la_pagina_principal(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'Controla el dinero de tu' in html
    assert 'cultivo de lulo' in html
    assert 'data-escritura' in html  # título con efecto de escritura
    assert 'js/landing.js' in html


def test_landing_tiene_enlaces_al_login_y_al_registro(client):
    html = client.get('/').data.decode()
    assert 'href="/login"' in html
    assert 'href="/User/add"' in html


def test_landing_explica_las_funciones(client):
    html = client.get('/').data.decode()
    for funcion in ['Tus cultivos', 'Gastos', 'Cosechas', 'Pagos', 'Calendario', 'Ganancias reales']:
        assert funcion in html


def test_landing_no_pide_iniciar_sesion(client):
    response = client.get('/')
    assert response.status_code == 200  # es pública, no redirige al login


def test_con_sesion_iniciada_la_landing_lleva_al_dashboard(logged_client):
    response = logged_client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_el_login_sigue_funcionando_en_su_nueva_direccion(client):
    assert client.get('/login').status_code == 200
    crear_usuario('lulero', clave='Clave2026x')
    response = client.post('/login', data={'nameUser': 'lulero', 'passwordUser': 'Clave2026x'})
    assert response.headers['Location'].endswith('/dashboard')


def test_paginas_privadas_mandan_al_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_pasos_tienen_flechas_entre_ellos(client):
    html = client.get('/').data.decode()
    assert html.count('class="landing-paso"') == 4
    assert html.count('class="landing-flecha"') == 3  # una flecha entre cada paso


def test_tarjetas_aparecen_al_bajar(client):
    html = client.get('/').data.decode()
    assert html.count('revelar') >= 15  # títulos, tarjetas y llamado final


def test_login_tiene_boton_para_volver_a_la_landing(client):
    html = client.get('/login').data.decode()
    assert 'Volver al inicio' in html
    assert 'href="/"' in html
