from app.models.cultivo import Cultivo
from tests.conftest import crear_usuario, crear_cultivo, iniciar_sesion


def test_crear_cultivo(logged_client, user):
    response = logged_client.post('/cultivos/add', data={
        'nombre': 'Lote Norte', 'hectareas': '2', 'fecha_sembrado': '2026-03-01', 'plantas': '',
    }, follow_redirects=True)
    assert 'Lote Norte'.encode() in response.data
    cultivo = Cultivo.query.filter_by(nombre='Lote Norte').first()
    assert cultivo.idUser == user.idUser
    assert cultivo.plantas == 1360  # sin plantas -> estimado de 680 por hectárea


def test_crear_cultivo_rechaza_hectareas_invalidas(logged_client):
    logged_client.post('/cultivos/add', data={
        'nombre': 'Malo', 'hectareas': '-1', 'fecha_sembrado': '2026-03-01',
    })
    assert Cultivo.query.filter_by(nombre='Malo').first() is None


def test_usuario_no_ve_cultivos_ajenos(client, user):
    otro = crear_usuario('otro')
    ajeno = crear_cultivo(otro, 'Lote Ajeno')
    iniciar_sesion(client, user)
    assert b'Lote Ajeno' not in client.get('/cultivos/').data
    for url in [f'/cultivos/dashboard/{ajeno.idCultivo}', f'/calendario/{ajeno.idCultivo}',
                f'/gastos/cultivo/{ajeno.idCultivo}', f'/ingresos/cultivo/{ajeno.idCultivo}',
                f'/pagos/cultivo/{ajeno.idCultivo}']:
        assert client.get(url).status_code in (404, 500), url


def test_eliminar_cultivo(logged_client, user):
    cultivo = crear_cultivo(user)
    logged_client.post(f'/cultivos/delete/{cultivo.idCultivo}')
    assert Cultivo.query.get(cultivo.idCultivo) is None
