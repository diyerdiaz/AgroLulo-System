from flask_login import current_user
from app.models.cultivo import Cultivo


def formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


def cultivo_de_usuario(id):
    """Trae el cultivo por id, pero solo si es del usuario que inició
    sesión: cada cuenta ve y administra únicamente sus propios cultivos."""
    return Cultivo.query.filter_by(idCultivo=id, idUser=current_user.idUser).first_or_404()
