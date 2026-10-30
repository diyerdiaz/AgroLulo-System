import pytest

from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo
from app.utils.helpers import numero_valido
from tests.conftest import crear_cultivo


@pytest.mark.parametrize('texto', ['nan', 'inf', '-inf', '1e400', '1e16'])
def test_numero_valido_rechaza_lo_que_no_es_una_cifra_real(texto):
    with pytest.raises(ValueError):
        numero_valido(texto)


def test_numero_valido_acepta_numeros_normales():
    assert numero_valido('2.5') == 2.5


@pytest.mark.parametrize('hectareas', ['nan', 'inf', '1e308'])
def test_cultivo_con_hectareas_invalidas_se_rechaza_con_mensaje(logged_client, hectareas):
    respuesta = logged_client.post('/cultivos/add', data={
        'nombre': 'Raro', 'hectareas': hectareas, 'fecha_sembrado': '2026-01-15',
    })
    assert respuesta.status_code == 302
    assert respuesta.headers['Location'].endswith('/cultivos/new')
    assert Cultivo.query.filter_by(nombre='Raro').first() is None


def test_gasto_infinito_se_rechaza(logged_client, user):
    cultivo = crear_cultivo(user)
    logged_client.post(f'/gastos/cultivo/{cultivo.idCultivo}/agregar', data={
        'tipo': 'otro', 'valor': 'inf', 'fecha': '2026-01-15',
    })
    assert GastoCultivo.query.count() == 0


@pytest.mark.parametrize('anio', [0, -5, 10000])
def test_calendario_con_anio_imposible_no_falla(logged_client, user, anio):
    cultivo = crear_cultivo(user)
    assert logged_client.get(f'/calendario/{cultivo.idCultivo}?year={anio}').status_code == 200
