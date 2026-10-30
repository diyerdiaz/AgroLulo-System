from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models.gasto import GastoCultivo
from app.models.ingreso import IngresoCultivo
from app.models.users import User
from app.utils.panel_admin import calcular_panel, hace_cuanto
from tests.conftest import crear_cultivo, crear_usuario, iniciar_sesion

SECCIONES_DEL_CULTIVADOR = ['/cultivos/', '/calendario/', '/ingresos/', '/gastos/', '/pagos/']


def plata(cultivo, ingresos=0, gastos=0):
    if ingresos:
        db.session.add(IngresoCultivo(idCultivo=cultivo.idCultivo, tipo='extra', valor=ingresos, fecha=date.today()))
    if gastos:
        db.session.add(GastoCultivo(idCultivo=cultivo.idCultivo, tipo='insumos', valor=gastos, fecha=date.today()))
    db.session.commit()


@pytest.fixture
def admin_client(client, admin):
    iniciar_sesion(client, admin)
    return client


# --- El admin no usa las secciones del cultivador ---

@pytest.mark.parametrize('url', SECCIONES_DEL_CULTIVADOR)
def test_admin_no_entra_a_secciones_del_cultivador(admin_client, url):
    r = admin_client.get(url)
    assert r.status_code == 302 and r.headers['Location'].endswith('/dashboard')


@pytest.mark.parametrize('url', SECCIONES_DEL_CULTIVADOR)
def test_cultivador_si_entra(logged_client, url):
    assert logged_client.get(url).status_code == 200


def test_admin_ve_su_panel_y_no_el_dashboard_del_cultivador(admin_client):
    html = admin_client.get('/dashboard').data.decode()
    assert 'Panel del Administrador' in html
    assert 'chartProduccionBarras' not in html
    assert 'id="donPancho"' not in html


@pytest.mark.parametrize('url', ['/dashboard', '/usuarios', '/perfil'])
def test_menu_del_admin_no_tiene_secciones_del_cultivador(admin_client, url):
    html = admin_client.get(url).data.decode()
    for seccion in SECCIONES_DEL_CULTIVADOR:
        assert f'href="{seccion}"' not in html, seccion
    assert 'Estadísticas de Usuarios' not in html


def test_menu_del_cultivador_sigue_completo(logged_client):
    html = logged_client.get('/perfil').data.decode()
    assert 'href="/cultivos/"' in html and 'href="/pagos/"' in html


# --- Sin cifras de los cultivadores ---

def test_panel_no_muestra_plata_de_nadie(admin_client, app):
    lulero = crear_usuario('lulero')
    plata(crear_cultivo(lulero, 'Lote Secreto'), ingresos=7654321, gastos=1234567)
    html = admin_client.get('/dashboard').data.decode()
    for cifra in ['7654321', '7.654.321', '1234567', '1.234.567', '6419754', '6.419.754']:
        assert cifra not in html
    assert 'Lote Secreto' not in html


def test_porcentajes_de_rentabilidad(app):
    uno, dos, tres = crear_usuario('uno'), crear_usuario('dos'), crear_usuario('tres')
    plata(crear_cultivo(uno), ingresos=1000, gastos=400)   # gana
    plata(crear_cultivo(dos), ingresos=200, gastos=800)    # pierde
    crear_cultivo(tres)                                    # sin datos
    panel = calcular_panel()
    assert panel['pct_cultivadores_rentables'] == 50
    assert panel['pct_cultivos_rentables'] == 50
    assert panel['margen_general'] == 0          # (1200 - 1200) / 1200
    assert panel['pct_sin_datos'] == 33


def test_el_admin_no_cuenta_como_cultivador(app, admin):
    plata(crear_cultivo(admin), ingresos=50, gastos=900)
    panel = calcular_panel()
    assert panel['hay_cultivadores'] is False


def test_solo_gastos_no_rompe_el_panel(admin_client, app):
    plata(crear_cultivo(crear_usuario('nuevo')), gastos=300)
    assert calcular_panel()['margen_general'] is None
    assert 'todavía no hay ventas registradas' in admin_client.get('/dashboard').data.decode()


# --- Actividad ---

def test_actividad_y_recientes(app):
    ahora = datetime.utcnow()
    for nombre, hace in [('hoy', timedelta(hours=2)), ('semana', timedelta(days=3)),
                         ('mes', timedelta(days=20)), ('nunca', None)]:
        u = crear_usuario(nombre)
        u.ultimo_acceso = ahora - hace if hace else None
    db.session.commit()
    panel = calcular_panel(ahora)
    assert [a['pct'] for a in panel['actividad']] == [25, 50, 75]
    assert panel['pct_nunca_entraron'] == 25
    assert [r['nombre'] for r in panel['recientes']] == ['hoy', 'semana', 'mes']
    assert panel['recientes'][0]['cuando'] == 'hace 2 h'


def test_iniciar_sesion_registra_el_acceso(client, app):
    crear_usuario('lulero', clave='Clave2026x')
    client.post('/login', data={'nameUser': 'lulero', 'passwordUser': 'Clave2026x'})
    assert User.query.filter_by(nameUser='lulero').one().ultimo_acceso is not None


def test_aviso_de_cuentas_esperando_activacion(admin_client, app):
    crear_usuario('pendiente', activo=False)
    assert 'Hay 1 cuenta esperando' in admin_client.get('/dashboard').data.decode()


@pytest.mark.parametrize('segundos, texto', [(30, 'hace un momento'), (25 * 60, 'hace 25 min'),
                                             (5 * 3600, 'hace 5 h'), (86400 + 60, 'ayer'),
                                             (6 * 86400, 'hace 6 días')])
def test_hace_cuanto(segundos, texto):
    ahora = datetime(2026, 10, 29, 12, 0)
    assert hace_cuanto(ahora - timedelta(seconds=segundos), ahora) == texto


# --- Comando crear-admin ---

def test_comando_crear_admin(app):
    r = app.test_cli_runner().invoke(args=['crear-admin', '--usuario', 'jefe'],
                                     input='debil\ndebil\nLuloFuerte2026\nLuloFuerte2026\n')
    assert 'La contraseña debe' in r.output          # rechaza la débil
    assert "cuenta administradora 'jefe' creada" in r.output
    jefe = User.query.filter_by(nameUser='jefe').one()
    assert jefe.isAdmin and jefe.activo and not jefe.debe_cambiar_password
    assert jefe.check_password('LuloFuerte2026')


def test_comando_crear_admin_se_rinde_tras_tres_intentos(app):
    r = app.test_cli_runner().invoke(args=['crear-admin'], input='debil\ndebil\n' * 3)
    assert r.exit_code != 0 and 'No se cambió nada' in r.output


# --- Ficha de cada cultivador (pasteles en porcentaje) ---

def test_el_nombre_en_interaccion_reciente_abre_su_ficha(admin_client, app):
    huka = crear_usuario('huka')
    huka.ultimo_acceso = datetime.utcnow()
    db.session.commit()
    html = admin_client.get('/dashboard').data.decode()
    assert f'href="/panel/cultivador/{huka.idUser}"' in html


def test_ficha_muestra_porcentajes_por_cultivo_sin_plata(admin_client, app):
    from app.models.actividad import ActividadCultivo
    huka = crear_usuario('huka')
    lote = crear_cultivo(huka, 'Lote El Mirador')
    plata(lote, ingresos=7654321, gastos=1234567)
    db.session.add(GastoCultivo(idCultivo=lote.idCultivo, tipo='mano_obra', valor=3765433, fecha=date.today()))
    db.session.add(ActividadCultivo(idCultivo=lote.idCultivo, tipo='fumigacion', fecha=date.today()))
    db.session.commit()

    html = admin_client.get(f'/panel/cultivador/{huka.idUser}').data.decode()
    assert 'Lote El Mirador' in html
    assert 'pastelUso' in html and 'pastelGastos' in html
    for cifra in ['7654321', '7.654.321', '1234567', '1.234.567', '3765433', '3.765.433']:
        assert cifra not in html, cifra
    # Gastos: 1.234.567 de insumos y 3.765.433 de mano de obra -> 24.7 % y 75.3 %
    assert '24.7' in html and '75.3' in html


def test_calculo_de_la_ficha(app):
    from app.utils.panel_admin import detalle_cultivador
    huka = crear_usuario('huka')
    gana = crear_cultivo(huka, 'Gana')
    pierde = crear_cultivo(huka, 'Pierde')
    crear_cultivo(huka, 'Vacio')
    plata(gana, ingresos=1000, gastos=250)
    plata(pierde, ingresos=100, gastos=400)
    ficha = detalle_cultivador(huka)
    assert ficha['pct_cultivos_rentables'] == 50
    por_nombre = {c['nombre']: c for c in ficha['cultivos']}
    assert por_nombre['Gana']['estado'] == 'gana' and por_nombre['Gana']['margen'] == 75
    assert por_nombre['Pierde']['estado'] == 'pierde' and por_nombre['Pierde']['margen'] == -300
    assert por_nombre['Vacio']['interaccion'] is None
    assert por_nombre['Gana']['interaccion']['data'] == [50.0, 50.0]   # 1 gasto, 1 cosecha
    assert ficha['reparto_cultivos']['labels'] == ['Gana', 'Pierde']


def test_cultivador_no_puede_ver_fichas(logged_client, app):
    otro = crear_usuario('otro')
    r = logged_client.get(f'/panel/cultivador/{otro.idUser}')
    assert r.status_code == 302 and r.headers['Location'].endswith('/dashboard')


def test_no_hay_ficha_del_admin(admin_client, admin):
    r = admin_client.get(f'/panel/cultivador/{admin.idUser}')
    assert r.status_code == 302


def test_desde_usuarios_se_abre_la_ficha(admin_client, app):
    huka = crear_usuario('huka')
    html = admin_client.get('/usuarios').data.decode()
    assert html.count(f'href="/panel/cultivador/{huka.idUser}"') == 2   # nombre y botón "Ver ficha"
    assert 'Ver ficha' in html


# --- Datos imaginarios ---

def test_datos_demo_se_crean_y_se_borran_sin_tocar_los_reales(app):
    from app.models.cultivo import Cultivo
    from app.utils.datos_demo import CANTIDAD_DEMO, borrar_datos_demo, crear_datos_demo
    real = crear_usuario('huka')
    crear_cultivo(real, 'Lote Real')

    usuarios, lotes = crear_datos_demo('Clave2026x')
    assert usuarios == CANTIDAD_DEMO and lotes >= CANTIDAD_DEMO - 2
    assert User.query.filter_by(activo=False).count() == 2
    assert calcular_panel()['hay_datos_rentabilidad']

    assert borrar_datos_demo() == CANTIDAD_DEMO
    assert [u.nameUser for u in User.query.filter_by(isAdmin=False)] == ['huka']
    assert [c.nombre for c in Cultivo.query.all()] == ['Lote Real']


def test_los_nombres_demo_se_inventan_cada_vez(app):
    from app.utils.datos_demo import borrar_datos_demo, crear_datos_demo
    crear_datos_demo('Clave2026x')
    primeros = {u.nameUser for u in User.query.filter_by(isAdmin=False)}
    borrar_datos_demo()
    crear_datos_demo('Clave2026x')
    segundos = {u.nameUser for u in User.query.filter_by(isAdmin=False)}
    assert primeros != segundos


def test_el_codigo_no_trae_nombres_de_usuario_fijos():
    import inspect
    from app.utils import datos_demo
    codigo = inspect.getsource(datos_demo)
    for viejo in ['juan_restrepo', 'maria_ospina', 'yesenia_toro', 'wilson_arango']:
        assert viejo not in codigo
