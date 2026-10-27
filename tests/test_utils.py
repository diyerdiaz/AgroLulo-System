from app.utils.helpers import formato_moneda
from app.utils.cosechas import paginar


def test_formato_moneda_usa_punto_de_miles():
    assert formato_moneda(1234567) == '1.234.567'
    assert formato_moneda(0) == '0'
    assert formato_moneda(999.6) == '1.000'


def test_paginar_primera_pagina():
    pagina, actual, total = paginar(list(range(12)), 1)
    assert pagina == [0, 1, 2, 3, 4] and actual == 1 and total == 3


def test_paginar_ajusta_paginas_fuera_de_rango():
    _, actual, total = paginar(list(range(12)), 99)
    assert actual == 3 and total == 3
    _, actual, _ = paginar([], None)
    assert actual == 1
