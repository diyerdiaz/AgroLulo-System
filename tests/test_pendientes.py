from datetime import date, timedelta

import pytest

from app import db
from app.models.actividad import ActividadCultivo
from app.utils.recordatorios import TEMAS, actividades_pendientes, armar_correo_recordatorio, ejemplos
from tests.conftest import crear_cultivo, crear_usuario, iniciar_sesion

HOY = date.today()


def actividad(cultivo, tipo='fumigacion', dias=0, hecha=False, nota=None):
    act = ActividadCultivo(idCultivo=cultivo.idCultivo, tipo=tipo, fecha=HOY + timedelta(days=dias),
                           nota=nota, hecha=hecha)
    db.session.add(act)
    db.session.commit()
    return act


# --- Qué cuenta como pendiente ---

def test_actividad_nueva_nace_sin_hacer(user):
    assert actividad(crear_cultivo(user)).hecha is False


def test_pendientes_incluye_hoy_y_dias_pasados(user):
    cultivo = crear_cultivo(user)
    hoy = actividad(cultivo, dias=0)
    ayer = actividad(cultivo, 'riego', dias=-1)
    vieja = actividad(cultivo, 'abono', dias=-10)
    assert actividades_pendientes(user.idUser) == [vieja, ayer, hoy]


def test_pendientes_no_incluye_futuras_ni_hechas(user):
    cultivo = crear_cultivo(user)
    actividad(cultivo, dias=2)
    actividad(cultivo, dias=-1, hecha=True)
    assert actividades_pendientes(user.idUser) == []


@pytest.mark.parametrize('tipo', ['cosecha', 'gasto', 'pago'])
def test_registros_automaticos_no_son_pendientes(user, tipo):
    actividad(crear_cultivo(user), tipo, dias=-1)
    assert actividades_pendientes(user.idUser) == []


def test_pendientes_solo_de_la_propia_cuenta(app, user):
    otro = crear_usuario('otro')
    actividad(crear_cultivo(otro), dias=-1)
    assert actividades_pendientes(user.idUser) == []


# --- Don Pancho pregunta al entrar ---

def test_don_pancho_pregunta_en_el_dashboard(logged_client, user):
    actividad(crear_cultivo(user, 'Lote El Mirador'), dias=-2, nota='Contra el pasador')
    html = logged_client.get('/dashboard').data.decode()
    assert 'id="panchoPregunta"' in html
    assert 'Lote El Mirador' in html
    assert 'hace 2 días' in html
    assert 'Contra el pasador' in html


@pytest.mark.parametrize('url', ['/calendario/', '/calendario/{id}'])
def test_don_pancho_pregunta_en_el_calendario(logged_client, user, url):
    cultivo = crear_cultivo(user)
    actividad(cultivo)
    assert 'id="panchoPregunta"' in logged_client.get(url.format(id=cultivo.idCultivo)).data.decode()


def test_sin_pendientes_no_pregunta(logged_client, user):
    actividad(crear_cultivo(user), dias=1)
    assert 'id="panchoPregunta"' not in logged_client.get('/dashboard').data.decode()


def test_despues_le_digo_no_vuelve_a_preguntar_hoy(logged_client, user):
    actividad(crear_cultivo(user), dias=-1)
    assert logged_client.post('/calendario/pendientes/despues').status_code == 200
    assert 'id="panchoPregunta"' not in logged_client.get('/dashboard').data.decode()


def test_al_iniciar_sesion_vuelve_a_preguntar(client, app):
    cuenta = crear_usuario('lulero', clave='Clave2026x')
    actividad(crear_cultivo(cuenta), dias=-1)
    iniciar_sesion(client, cuenta)
    client.post('/calendario/pendientes/despues')
    client.post('/login', data={'nameUser': 'lulero', 'passwordUser': 'Clave2026x'})
    assert 'id="panchoPregunta"' in client.get('/dashboard').data.decode()


def test_calendario_recarga_al_marcar_y_dashboard_no(logged_client, user):
    cultivo = crear_cultivo(user)
    actividad(cultivo)
    assert 'data-recargar="1"' in logged_client.get(f'/calendario/{cultivo.idCultivo}').data.decode()
    assert 'data-recargar="0"' in logged_client.get('/dashboard').data.decode()


# --- Marcar como hecho (el mismo día o después) ---

@pytest.mark.parametrize('dias', [0, -1, -7])
def test_marcar_hecha_sirve_aunque_se_haya_pasado_el_dia(logged_client, user, dias):
    cultivo = crear_cultivo(user)
    act = actividad(cultivo, dias=dias)
    r = logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad/{act.idActividad}/hecha',
                           headers={'Accept': 'application/json'})
    assert r.get_json() == {'ok': True}
    assert act.hecha is True and act.fecha_hecha is not None
    assert actividades_pendientes(user.idUser) == []


def test_marcar_hecha_desde_formulario_redirige_al_calendario(logged_client, user):
    cultivo = crear_cultivo(user)
    act = actividad(cultivo)
    r = logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad/{act.idActividad}/hecha')
    assert r.status_code == 302 and f'/calendario/{cultivo.idCultivo}' in r.headers['Location']


def test_desmarcar_vuelve_a_pendiente(logged_client, user):
    cultivo = crear_cultivo(user)
    act = actividad(cultivo, dias=-1, hecha=True)
    logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad/{act.idActividad}/pendiente')
    assert act.hecha is False
    assert actividades_pendientes(user.idUser) == [act]


def test_no_se_puede_marcar_trabajo_de_otra_cuenta(logged_client, app):
    otro = crear_usuario('otro')
    cultivo = crear_cultivo(otro)
    act = actividad(cultivo)
    r = logged_client.post(f'/calendario/{cultivo.idCultivo}/actividad/{act.idActividad}/hecha')
    # El manejador de errores general de la app convierte el 404 en 500
    # (igual que en test_cultivos.py); lo importante es que no lo marca.
    assert r.status_code in (404, 500)
    assert act.hecha is False


def test_calendario_muestra_estado_y_boton_listo(logged_client, user):
    cultivo = crear_cultivo(user)
    actividad(cultivo, dias=-1)
    actividad(cultivo, 'riego', dias=-2, hecha=True)
    actividad(cultivo, 'abono', dias=3)
    html = logged_client.get(f'/calendario/{cultivo.idCultivo}').data.decode()
    assert 'Pendiente' in html and '✔ Hecho' in html and 'Programado' in html
    assert 'Listo' in html


# --- Correos ---

def test_los_correos_no_tienen_boton_ya_lo_hice(app):
    with app.test_request_context():
        for hoy, atrasadas in ejemplos():
            html = armar_correo_recordatorio('Diyer', hoy, atrasadas)[2]
            assert 'Ya lo hice' not in html
            assert 'Abrir mi calendario' in html


def test_hay_siete_plantillas(app):
    assert len(TEMAS) == 7
    with app.test_request_context():
        asuntos = {armar_correo_recordatorio('Diyer', h, a)[0].split('·')[0] for h, a in ejemplos()}
    assert len(asuntos) == 7
