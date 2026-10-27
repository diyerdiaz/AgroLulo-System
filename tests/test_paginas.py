import pytest
from tests.conftest import crear_cultivo


PAGINAS = ['/dashboard', '/perfil', '/cultivos/', '/cultivos/new', '/calendario/',
           '/gastos/', '/ingresos/', '/pagos/']

PAGINAS_DE_CULTIVO = ['/cultivos/dashboard/{id}', '/cultivos/editar/{id}', '/calendario/{id}',
                      '/gastos/cultivo/{id}', '/ingresos/cultivo/{id}', '/pagos/cultivo/{id}']


@pytest.mark.parametrize('url', PAGINAS)
def test_paginas_cargan_sin_cultivos(logged_client, url):
    assert logged_client.get(url).status_code == 200


@pytest.mark.parametrize('url', PAGINAS + PAGINAS_DE_CULTIVO)
def test_paginas_cargan_con_un_cultivo(logged_client, user, url):
    cultivo = crear_cultivo(user)
    assert logged_client.get(url.format(id=cultivo.idCultivo)).status_code == 200
