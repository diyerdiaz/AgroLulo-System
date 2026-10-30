from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.cultivo import Cultivo
from app.models.actividad import ActividadCultivo, TIPOS_ACTIVIDAD, TIPOS_SELECCIONABLES
from app.utils.helpers import cultivo_de_usuario
from app.utils.recordatorios import pendientes_para_preguntar, posponer_pregunta
from app import db
import calendar
from datetime import date, datetime

bp = Blueprint('calendario', __name__, url_prefix='/calendario')

MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]
DIAS_SEMANA_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


@bp.app_context_processor
def _pendientes_don_pancho():
    # partials/pendientes_don_pancho.html la llama para saber si Don Pancho
    # tiene que preguntar por trabajos sin marcar (solo se consulta en las
    # páginas que incluyen ese partial).
    return {'pendientes_don_pancho': pendientes_para_preguntar}


@bp.route('/')
@login_required
def index():
    """Lista todos los cultivos para elegir a cuál ver el calendario."""
    cultivos = Cultivo.query.filter_by(idUser=current_user.idUser).order_by(Cultivo.idCultivo.desc()).all()
    return render_template('calendario/index.html', cultivos=cultivos)


@bp.route('/<int:id>')
@login_required
def ver(id):
    """Calendario mensual de un cultivo específico, navegable por mes/año."""
    cultivo = cultivo_de_usuario(id)

    hoy = date.today()
    year = request.args.get('year', hoy.year, type=int)
    month = request.args.get('month', hoy.month, type=int)

    # Si la navegación se sale de rango (0 o 13), pasar al año contiguo
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    cal = calendar.Calendar(firstweekday=0)  # Semanas de Lunes a Domingo
    semanas = cal.monthdayscalendar(year, month)

    mes_anterior, anio_anterior = (12, year - 1) if month == 1 else (month - 1, year)
    mes_siguiente, anio_siguiente = (1, year + 1) if month == 12 else (month + 1, year)

    # Días a resaltar visualmente en la celda (fondo azul = fecha de sembrado)
    fechas_destacadas = set()
    if cultivo.fecha_sembrado and cultivo.fecha_sembrado.year == year and cultivo.fecha_sembrado.month == month:
        fechas_destacadas.add(cultivo.fecha_sembrado.day)

    # Etiquetas por día: se arma un diccionario {'AAAA-MM-DD': [ {...}, ... ]}
    # combinando las etiquetas guardadas en la base de datos con las
    # "automáticas" que se derivan del propio registro del cultivo
    # (creación y siembra), para que aparezcan como una etiqueta más
    # al espichar el día en el calendario.
    actividades_por_dia = {}

    def _agregar(fecha_iso, entrada):
        actividades_por_dia.setdefault(fecha_iso, []).append(entrada)

    if cultivo.fecha_creacion and cultivo.fecha_creacion.year == year and cultivo.fecha_creacion.month == month:
        meta = TIPOS_ACTIVIDAD['creacion']
        _agregar(cultivo.fecha_creacion.strftime('%Y-%m-%d'), {
            'id': None,
            'tipo': 'creacion',
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'nota': f"Se registró el lote '{cultivo.nombre}' en el sistema.",
            'eliminable': False,
        })

    if cultivo.fecha_sembrado and cultivo.fecha_sembrado.year == year and cultivo.fecha_sembrado.month == month:
        meta = TIPOS_ACTIVIDAD['siembra']
        _agregar(cultivo.fecha_sembrado.strftime('%Y-%m-%d'), {
            'id': None,
            'tipo': 'siembra',
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'nota': f"Fecha de siembra de '{cultivo.nombre}'.",
            'eliminable': False,
        })

    inicio_mes = date(year, month, 1)
    fin_mes = date(year, month, calendar.monthrange(year, month)[1])
    actividades_bd = (
        ActividadCultivo.query
        .filter(ActividadCultivo.idCultivo == id)
        .filter(ActividadCultivo.fecha >= inicio_mes)
        .filter(ActividadCultivo.fecha <= fin_mes)
        .order_by(ActividadCultivo.idActividad.asc())
        .all()
    )
    for act in actividades_bd:
        _agregar(act.fecha.strftime('%Y-%m-%d'), act.to_dict())

    # Historial completo del cultivo (todas las etiquetas, sin importar el
    # mes que se esté viendo), para el botón "Ver Etiquetas" de arriba.
    todas_actividades = []

    if cultivo.fecha_creacion:
        meta = TIPOS_ACTIVIDAD['creacion']
        todas_actividades.append({
            'id': None,
            'tipo': 'creacion',
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'nota': f"Se registró el lote '{cultivo.nombre}' en el sistema.",
            'eliminable': False,
            'fecha': cultivo.fecha_creacion.date(),
        })

    if cultivo.fecha_sembrado:
        meta = TIPOS_ACTIVIDAD['siembra']
        todas_actividades.append({
            'id': None,
            'tipo': 'siembra',
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'nota': f"Fecha de siembra de '{cultivo.nombre}'.",
            'eliminable': False,
            'fecha': cultivo.fecha_sembrado,
        })

    actividades_todas_bd = (
        ActividadCultivo.query
        .filter(ActividadCultivo.idCultivo == id)
        .order_by(ActividadCultivo.fecha.desc(), ActividadCultivo.idActividad.desc())
        .all()
    )
    for act in actividades_todas_bd:
        datos = act.to_dict()
        datos['fecha'] = act.fecha
        todas_actividades.append(datos)

    todas_actividades.sort(key=lambda a: a['fecha'], reverse=True)

    return render_template(
        'calendario/ver.html',
        cultivo=cultivo,
        semanas=semanas,
        dias_semana=DIAS_SEMANA_ES,
        mes_nombre=MESES_ES[month],
        year=year,
        month=month,
        hoy=hoy,
        mes_anterior=mes_anterior,
        anio_anterior=anio_anterior,
        mes_siguiente=mes_siguiente,
        anio_siguiente=anio_siguiente,
        fechas_destacadas=fechas_destacadas,
        tipos_actividad=TIPOS_SELECCIONABLES,
        actividades_por_dia=actividades_por_dia,
        todas_actividades=todas_actividades,
    )


@bp.route('/<int:id>/actividad', methods=['POST'])
@login_required
def agregar_actividad(id):
    """Agrega una etiqueta/actividad a un día del calendario del cultivo."""
    cultivo = cultivo_de_usuario(id)

    fecha_raw = request.form.get('fecha', '').strip()
    tipo = request.form.get('tipo', '').strip()
    nota = request.form.get('nota', '').strip()
    year = request.form.get('year', type=int) or date.today().year
    month = request.form.get('month', type=int) or date.today().month

    if tipo not in TIPOS_SELECCIONABLES:
        flash('Selecciona un tipo de etiqueta válido.', 'danger')
        return redirect(url_for('calendario.ver', id=cultivo.idCultivo, year=year, month=month))

    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('calendario.ver', id=cultivo.idCultivo, year=year, month=month))

    nueva = ActividadCultivo(idCultivo=cultivo.idCultivo, tipo=tipo, fecha=fecha, nota=nota or None)
    db.session.add(nueva)
    db.session.commit()

    flash(f"Etiqueta '{TIPOS_ACTIVIDAD[tipo]['label']}' agregada al {fecha.strftime('%d/%m/%Y')}.", 'success')
    return redirect(url_for('calendario.ver', id=cultivo.idCultivo, year=fecha.year, month=fecha.month))


@bp.route('/<int:id>/actividad/<int:actividad_id>/eliminar', methods=['POST'])
@login_required
def eliminar_actividad(id, actividad_id):
    """Elimina una etiqueta/actividad registrada manualmente."""
    cultivo_de_usuario(id)
    actividad = ActividadCultivo.query.filter_by(idActividad=actividad_id, idCultivo=id).first_or_404()
    year = request.form.get('year', type=int) or date.today().year
    month = request.form.get('month', type=int) or date.today().month

    db.session.delete(actividad)
    db.session.commit()

    flash('Etiqueta eliminada.', 'info')
    return redirect(url_for('calendario.ver', id=id, year=year, month=month))


def _quiere_json():
    return request.accept_mimetypes.best == 'application/json' or request.is_json


@bp.route('/<int:id>/actividad/<int:actividad_id>/hecha', methods=['POST'])
@login_required
def marcar_hecha(id, actividad_id):
    """Marca un trabajo como hecho. Sirve el mismo día o cualquier día
    después (si se le pasó y lo hizo tarde)."""
    cultivo_de_usuario(id)
    actividad = ActividadCultivo.query.filter_by(idActividad=actividad_id, idCultivo=id).first_or_404()
    if not actividad.hecha:
        actividad.hecha = True
        actividad.fecha_hecha = datetime.utcnow()
        db.session.commit()

    if _quiere_json():
        return jsonify(ok=True)
    flash(f"¡Eso es, mano! '{TIPOS_ACTIVIDAD.get(actividad.tipo, TIPOS_ACTIVIDAD['otro'])['label']}' "
          f"quedó marcado como hecho.", 'success')
    return redirect(url_for('calendario.ver', id=id, year=actividad.fecha.year, month=actividad.fecha.month))


@bp.route('/<int:id>/actividad/<int:actividad_id>/pendiente', methods=['POST'])
@login_required
def marcar_pendiente(id, actividad_id):
    """Deshace "hecho" (por si se marcó por error)."""
    cultivo_de_usuario(id)
    actividad = ActividadCultivo.query.filter_by(idActividad=actividad_id, idCultivo=id).first_or_404()
    actividad.hecha = False
    actividad.fecha_hecha = None
    db.session.commit()

    if _quiere_json():
        return jsonify(ok=True)
    flash('Listo, quedó otra vez como pendiente.', 'info')
    return redirect(url_for('calendario.ver', id=id, year=actividad.fecha.year, month=actividad.fecha.month))


@bp.route('/pendientes/despues', methods=['POST'])
@login_required
def pendientes_despues():
    """ "Después le digo": Don Pancho no vuelve a preguntar hoy (o hasta el
    próximo inicio de sesión)."""
    posponer_pregunta()
    return jsonify(ok=True)
