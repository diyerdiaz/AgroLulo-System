from app.models.ingreso import IngresoCultivo


def grupo_de(ingreso):
    """La clave de agrupación de una cogida: su idCogida, o su propio
    idIngreso si es un registro viejo de antes de que existiera el
    agrupamiento (así cada uno queda como su propia Cosecha)."""
    return ingreso.idCogida or ingreso.idIngreso


def filas_de_cosecha(id_cultivo, grupo_id):
    """Todos los registros (Grueso/Parejo/Riche) que pertenecen a una misma
    Cosecha dentro de un cultivo."""
    filas = IngresoCultivo.query.filter_by(idCultivo=id_cultivo, idCogida=grupo_id).all()
    if filas:
        return filas
    solo = IngresoCultivo.query.filter_by(idCultivo=id_cultivo, idIngreso=grupo_id, idCogida=None).first()
    return [solo] if solo else []


COSECHAS_POR_PAGINA = 5


def paginar(lista, pagina_solicitada):
    """Recorta una lista ya ordenada a la página pedida (5 por página), y
    devuelve también en qué página quedó realmente y cuántas hay en total,
    para poder pintar los botones de Anterior/Siguiente."""
    total = len(lista)
    total_paginas = max(1, (total + COSECHAS_POR_PAGINA - 1) // COSECHAS_POR_PAGINA)
    pagina = max(1, min(pagina_solicitada or 1, total_paginas))
    inicio = (pagina - 1) * COSECHAS_POR_PAGINA
    return lista[inicio:inicio + COSECHAS_POR_PAGINA], pagina, total_paginas
