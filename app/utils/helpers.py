import math

from flask_login import current_user
from app.models.cultivo import Cultivo

# Ningún cultivo llega a estas cifras; solo evita números absurdos.
NUMERO_MAXIMO = 1e15


def formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


def numero_valido(valor):
    """Igual que float(), pero también rechaza con ValueError lo que Python
    acepta como número y no lo es de verdad: 'nan', 'inf' o cifras enormes."""
    numero = float(valor)
    if not math.isfinite(numero) or abs(numero) > NUMERO_MAXIMO:
        raise ValueError('Número fuera de rango')
    return numero


def cultivo_de_usuario(id):
    """Trae el cultivo por id, pero solo si es del usuario que inició
    sesión: cada cuenta ve y administra únicamente sus propios cultivos."""
    return Cultivo.query.filter_by(idCultivo=id, idUser=current_user.idUser).first_or_404()
