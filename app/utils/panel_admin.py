"""
Cálculos del panel del administrador (auth/dashboard_admin.html).

Regla: el administrador NO ve plata ni cifras de ningún cultivador. Todo lo
que sale de aquí son porcentajes de la plataforma completa (qué tanto de la
gente gana plata y qué tan activa está) y la lista de quién ha entrado
hace poco, sin ningún dato de sus cultivos.
"""
from datetime import datetime, timedelta

from app import db
from app.models.actividad import ActividadCultivo
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app.models.ingreso import IngresoCultivo
from app.models.users import User

RECIENTES_A_MOSTRAR = 8


def _porcentaje(parte, total):
    return round(parte * 100 / total) if total else 0


def ahora_utc():
    return datetime.utcnow()


def hace_cuanto(momento, ahora=None):
    """'hace un momento', 'hace 25 min', 'hace 3 h', 'ayer', 'hace 6 días' o 'nunca'."""
    if not momento:
        return 'nunca'
    segundos = ((ahora or ahora_utc()) - momento).total_seconds()
    if segundos < 120:
        return 'hace un momento'
    if segundos < 3600:
        return f'hace {int(segundos // 60)} min'
    if segundos < 86400:
        return f'hace {int(segundos // 3600)} h'
    dias = int(segundos // 86400)
    return 'ayer' if dias == 1 else f'hace {dias} días'


def _totales_por_cultivo():
    """{idCultivo: (ingresos, gastos)} con lo realmente registrado. Se usa
    solo para saber si cada cultivo gana o pierde; nunca sale del módulo."""
    ingresos = dict(db.session.query(IngresoCultivo.idCultivo, db.func.sum(IngresoCultivo.valor))
                    .group_by(IngresoCultivo.idCultivo).all())
    gastos = dict(db.session.query(GastoCultivo.idCultivo, db.func.sum(GastoCultivo.valor))
                  .group_by(GastoCultivo.idCultivo).all())
    return {c: (ingresos.get(c) or 0.0, gastos.get(c) or 0.0) for c in set(ingresos) | set(gastos)}


def calcular_panel(ahora=None):
    ahora = ahora or ahora_utc()
    cultivadores = User.query.filter_by(isAdmin=False).all()
    activos = [u for u in cultivadores if u.activo]
    ids_cultivadores = {u.idUser for u in cultivadores}

    # --- Rentabilidad (solo con lo realmente registrado en Ingresos/Gastos) ---
    totales = _totales_por_cultivo()
    cultivos = Cultivo.query.filter(Cultivo.idUser.in_(ids_cultivadores)).all() if ids_cultivadores else []

    por_usuario = {}
    cultivos_con_datos = cultivos_rentables = 0
    ingresos_plataforma = gastos_plataforma = 0.0
    for c in cultivos:
        ing, gas = totales.get(c.idCultivo, (0.0, 0.0))
        if ing <= 0 and gas <= 0:
            continue
        cultivos_con_datos += 1
        cultivos_rentables += ing > gas
        ingresos_plataforma += ing
        gastos_plataforma += gas
        acumulado = por_usuario.setdefault(c.idUser, [0.0, 0.0])
        acumulado[0] += ing
        acumulado[1] += gas

    usuarios_con_datos = len(por_usuario)
    usuarios_rentables = sum(1 for ing, gas in por_usuario.values() if ing > gas)
    margen_general = (round((ingresos_plataforma - gastos_plataforma) * 100 / ingresos_plataforma)
                      if ingresos_plataforma > 0 else None)

    # --- Actividad en la plataforma (sobre las cuentas activas) ---
    def activos_desde(delta):
        return sum(1 for u in activos if u.ultimo_acceso and ahora - u.ultimo_acceso <= delta)

    recientes = sorted((u for u in cultivadores if u.ultimo_acceso),
                       key=lambda u: u.ultimo_acceso, reverse=True)[:RECIENTES_A_MOSTRAR]

    return {
        'hay_cultivadores': bool(cultivadores),
        'hay_datos_rentabilidad': usuarios_con_datos > 0,
        'pct_cultivadores_rentables': _porcentaje(usuarios_rentables, usuarios_con_datos),
        'pct_cultivos_rentables': _porcentaje(cultivos_rentables, cultivos_con_datos),
        'margen_general': margen_general,
        'pct_sin_datos': _porcentaje(len(cultivadores) - usuarios_con_datos, len(cultivadores)),
        'actividad': [
            {'titulo': 'Últimas 24 horas', 'pct': _porcentaje(activos_desde(timedelta(days=1)), len(activos))},
            {'titulo': 'Últimos 7 días', 'pct': _porcentaje(activos_desde(timedelta(days=7)), len(activos))},
            {'titulo': 'Últimos 30 días', 'pct': _porcentaje(activos_desde(timedelta(days=30)), len(activos))},
        ],
        'pct_nunca_entraron': _porcentaje(sum(1 for u in activos if not u.ultimo_acceso), len(activos)),
        'recientes': [{'id': u.idUser, 'nombre': u.nameUser, 'cuando': hace_cuanto(u.ultimo_acceso, ahora),
                       'activo': u.activo}
                      for u in recientes],
        'esperando_activacion': sum(1 for u in cultivadores if not u.activo),
    }


# --- Ficha de un cultivador (auth/detalle_cultivador.html) ---
# Igual que el panel: solo porcentajes. Ningún monto sale de este módulo.

PALETA_CULTIVOS = ['#39ff14', '#4cc9f0', '#ffb703', '#b5179e', '#ff4d4d', '#06d6a0', '#8338ec', '#f72585']

# Cómo ha usado la cuenta en cada cultivo: qué tanto de lo que registra es
# de cada sección de la página.
INTERACCIONES = [
    ('gastos', 'Gastos', '#ff4d4d'),
    ('cosechas', 'Cosechas', '#39ff14'),
    ('pagos', 'Pagos recibidos', '#06d6a0'),
    ('calendario', 'Trabajos en el calendario', '#8338ec'),
]
# Etiquetas del calendario que se crean solas al llenar otras secciones;
# no cuentan como uso del calendario.
_TIPOS_AUTOMATICOS = {'creacion', 'cosecha', 'gasto', 'pago'}


def _pastel(pares):
    """[(etiqueta, cantidad, color)] -> {'labels', 'data' (% enteros), 'colores'},
    sin las porciones en cero. None si no hay nada."""
    pares = [p for p in pares if p[1] > 0]
    total = sum(p[1] for p in pares)
    if not total:
        return None
    return {'labels': [p[0] for p in pares],
            'data': [round(p[1] * 100 / total, 1) for p in pares],
            'colores': [p[2] for p in pares]}


def _meses_desde(fecha, hoy):
    meses = (hoy.year - fecha.year) * 12 + hoy.month - fecha.month
    if meses <= 0:
        return 'este mes'
    return 'hace 1 mes' if meses == 1 else f'hace {meses} meses'


def detalle_cultivador(usuario, ahora=None):
    ahora = ahora or ahora_utc()
    cultivos = Cultivo.query.filter_by(idUser=usuario.idUser).order_by(Cultivo.idCultivo.asc()).all()

    fichas = []
    registros_por_cultivo = []
    rentables = con_datos = 0
    for idx, c in enumerate(cultivos):
        gastos = GastoCultivo.query.filter_by(idCultivo=c.idCultivo).all()
        ingresos = IngresoCultivo.query.filter_by(idCultivo=c.idCultivo).all()
        actividades = [a for a in ActividadCultivo.query.filter_by(idCultivo=c.idCultivo).all()
                       if a.tipo not in _TIPOS_AUTOMATICOS]

        # Una cosecha puede ocupar varias filas (una por tipo de lulo):
        # se cuenta una vez por grupo.
        cosechas = {i.idCogida or -i.idIngreso for i in ingresos}
        pagos = {i.idCogida or -i.idIngreso for i in ingresos if (i.monto_pagado or 0) > 0}
        cantidades = {'gastos': len(gastos), 'cosechas': len(cosechas),
                      'pagos': len(pagos), 'calendario': len(actividades)}
        total_registros = sum(cantidades.values())

        suma_ing = sum(i.valor or 0 for i in ingresos)
        suma_gas = sum(g.valor or 0 for g in gastos)
        if suma_ing > 0 or suma_gas > 0:
            con_datos += 1
            rentables += suma_ing > suma_gas
        margen = round((suma_ing - suma_gas) * 100 / suma_ing) if suma_ing > 0 else None
        estado = 'sin datos' if not (suma_ing or suma_gas) else ('gana' if suma_ing > suma_gas else 'pierde')

        por_categoria = {}
        for g in gastos:
            por_categoria[g.tipo] = por_categoria.get(g.tipo, 0) + (g.valor or 0)

        fechas = ([g.fecha_registro for g in gastos] + [i.fecha_registro for i in ingresos]
                  + [a.fecha_creacion for a in actividades])
        fechas = [f for f in fechas if f]

        color = PALETA_CULTIVOS[idx % len(PALETA_CULTIVOS)]
        registros_por_cultivo.append((c.nombre, total_registros, color))
        fichas.append({
            'id': c.idCultivo,
            'nombre': c.nombre,
            'color': color,
            'sembrado': _meses_desde(c.fecha_sembrado, ahora.date()) if c.fecha_sembrado else None,
            'ultima_actividad': hace_cuanto(max(fechas), ahora) if fechas else 'nunca',
            'margen': margen,
            'estado': estado,
            'interaccion': _pastel([(nombre, cantidades[clave], col) for clave, nombre, col in INTERACCIONES]),
            'gastos': _pastel([(meta['label'], por_categoria.get(tipo, 0), meta['color'])
                               for tipo, meta in TIPOS_GASTO.items()]),
        })

    return {
        'nombre': usuario.nameUser,
        'activo': usuario.activo,
        'ultimo_acceso': hace_cuanto(usuario.ultimo_acceso, ahora),
        'pct_cultivos_rentables': _porcentaje(rentables, con_datos) if con_datos else None,
        'reparto_cultivos': _pastel(registros_por_cultivo),
        'cultivos': fichas,
    }
