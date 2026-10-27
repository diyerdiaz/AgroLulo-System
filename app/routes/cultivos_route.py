from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.cultivo import Cultivo
from app.models.ingreso import IngresoCultivo, TIPOS_INGRESO, TIPOS_LULO_COGIDA
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app.models.actividad import ActividadCultivo
from app.utils.helpers import cultivo_de_usuario
from app import db
from datetime import datetime, time

bp = Blueprint('cultivos', __name__, url_prefix='/cultivos')


@bp.route('/')
@login_required
def index():
    fecha_inicio_raw = request.args.get('fecha_inicio', '').strip()
    fecha_fin_raw = request.args.get('fecha_fin', '').strip()

    query = Cultivo.query.filter_by(idUser=current_user.idUser)

    if fecha_inicio_raw:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_raw, '%Y-%m-%d')
            query = query.filter(Cultivo.fecha_creacion >= datetime.combine(fecha_inicio, time.min))
        except ValueError:
            pass

    if fecha_fin_raw:
        try:
            fecha_fin = datetime.strptime(fecha_fin_raw, '%Y-%m-%d')
            query = query.filter(Cultivo.fecha_creacion <= datetime.combine(fecha_fin, time.max))
        except ValueError:
            pass

    cultivos = query.order_by(Cultivo.idCultivo.desc()).all()

    filas = []
    for c in cultivos:
        datos = c.to_dict()

        # Igual que en Ingresos/Gastos/Dashboard: si ya hay ingresos o
        # gastos registrados de verdad para este cultivo, esos mandan sobre
        # el 0 con el que arranca un cultivo recién creado.
        ingresos_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()
        gastos_reales = db.session.query(
            db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
        ).filter(GastoCultivo.idCultivo == c.idCultivo).scalar()
        produccion_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.cantidad_canastillas * IngresoCultivo.peso_canastilla), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()

        if ingresos_reales and ingresos_reales > 0:
            datos['ingresos'] = ingresos_reales
        if gastos_reales and gastos_reales > 0:
            datos['gastos'] = gastos_reales
        if produccion_reales and produccion_reales > 0:
            datos['produccion'] = produccion_reales

        datos['idCultivo'] = c.idCultivo
        datos['fecha_creacion'] = c.fecha_creacion
        datos['fecha_sembrado'] = c.fecha_sembrado
        filas.append(datos)

    return render_template(
        'cultivos/index.html',
        cultivos=filas,
        fecha_inicio=fecha_inicio_raw,
        fecha_fin=fecha_fin_raw
    )

@bp.route('/new')
@login_required
def new():
    return render_template('cultivos/new.html')

@bp.route('/add', methods=['POST'])
@login_required
def add():
    nombre = request.form.get('nombre', '').strip()
    hectareas_raw = request.form.get('hectareas', '0').strip()
    fecha_sembrado_raw = request.form.get('fecha_sembrado', '').strip()

    if not nombre or not hectareas_raw or not fecha_sembrado_raw:
        flash("Por favor ingrese todos los campos obligatorios.", "danger")
        return redirect(url_for('cultivos.new'))

    try:
        hectareas = float(hectareas_raw)
        if hectareas <= 0:
            raise ValueError()
    except ValueError:
        flash("Las hectáreas deben ser un número mayor a cero.", "danger")
        return redirect(url_for('cultivos.new'))

    try:
        fecha_sembrado = datetime.strptime(fecha_sembrado_raw, '%Y-%m-%d').date()
    except ValueError:
        flash("Fecha de sembrado inválida.", "danger")
        return redirect(url_for('cultivos.new'))

    # La cantidad de plantas se sugiere por capacidad física de la hectárea
    # (~680 matas por hectárea), pero el usuario puede escribir la cantidad
    # real que sembró y esa es la que manda. Solo si el campo llega vacío o
    # con un valor inválido se usa el estimado como respaldo. Producción,
    # ingresos y gastos NO se inventan a partir de las hectáreas: el
    # cultivo arranca en 0 en esos tres y solo cambian cuando el usuario
    # los registra de verdad más adelante (en Ingresos, Gastos, etc.).
    plantas_raw = request.form.get('plantas', '').strip()
    try:
        plantas = int(float(plantas_raw))
        if plantas < 0:
            raise ValueError()
    except ValueError:
        plantas = int(hectareas * 680)

    nuevo_cultivo = Cultivo(
        idUser=current_user.idUser,
        nombre=nombre,
        hectareas=hectareas,
        fecha_sembrado=fecha_sembrado,
        plantas=plantas,
    )

    db.session.add(nuevo_cultivo)
    db.session.commit()

    flash(f"¡Cultivo '{nombre}' registrado exitosamente!", "success")
    return redirect(url_for('cultivos.index'))

@bp.route('/dashboard/<int:id>')
@login_required
def dashboard(id):
    cultivo = cultivo_de_usuario(id)
    datos = cultivo.to_dict()

    # Igual que en Ingresos/Gastos: si el cultivo ya tiene ingresos o gastos
    # registrados de verdad, esos son los que mandan (si no hay ninguno,
    # queda en 0, no se inventa nada a partir de las hectáreas).
    ingresos_reales = db.session.query(
        db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
    ).filter(IngresoCultivo.idCultivo == id).scalar()
    gastos_reales = db.session.query(
        db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
    ).filter(GastoCultivo.idCultivo == id).scalar()

    # Producción por tipo de lulo (grueso/parejo/riche) de ESTE cultivo,
    # contando también los kilos sueltos que hayan sobrado en cada cogida
    # (igual que ya se hace en Ingresos y en el Dashboard General).
    filas_ingreso = IngresoCultivo.query.filter_by(idCultivo=id).all()
    produccion_por_tipo = {t: 0.0 for t in TIPOS_LULO_COGIDA}
    for fila in filas_ingreso:
        if fila.tipo in produccion_por_tipo:
            produccion_por_tipo[fila.tipo] += fila.kilos
    produccion_reales = sum(produccion_por_tipo.values())

    if ingresos_reales and ingresos_reales > 0:
        datos['ingresos'] = ingresos_reales
    if gastos_reales and gastos_reales > 0:
        datos['gastos'] = gastos_reales
    if produccion_reales and produccion_reales > 0:
        datos['produccion'] = produccion_reales
    datos['ganancias'] = datos['ingresos'] - datos['gastos']

    # --- Los mismos dos gráficos del Dashboard General ("Producción por
    # Cultivo" y "Gastos vs. Inversión & Utilidad"), pero calculados solo
    # con los datos reales de ESTE cultivo, no de todos ---
    bar_labels = [TIPOS_INGRESO[t]['label'] for t in TIPOS_LULO_COGIDA]
    bar_colores = [TIPOS_INGRESO[t]['color'] for t in TIPOS_LULO_COGIDA]
    bar_datos = [round(produccion_por_tipo[t], 1) for t in TIPOS_LULO_COGIDA]

    gastos_categoria_reales = dict(
        db.session.query(GastoCultivo.tipo, db.func.sum(GastoCultivo.valor))
        .filter(GastoCultivo.idCultivo == id)
        .group_by(GastoCultivo.tipo).all()
    )
    utilidad_real = (ingresos_reales or 0.0) - (gastos_reales or 0.0)

    pie_labels = ['Utilidad Neta (Ganancia)'] + [TIPOS_GASTO[t]['label'] for t in TIPOS_GASTO]
    pie_colores = ['#39ff14'] + [TIPOS_GASTO[t]['color'] for t in TIPOS_GASTO]
    pie_datos = [max(utilidad_real, 0.0)] + [gastos_categoria_reales.get(t, 0.0) for t in TIPOS_GASTO]

    chart_data = {
        'produccion': {
            'labels': bar_labels, 'data': bar_datos, 'colores': bar_colores,
            'hay_datos': sum(bar_datos) > 0,
        },
        'pie': {
            'labels': pie_labels, 'data': pie_datos, 'colores': pie_colores,
            'hay_datos': (ingresos_reales or 0.0) > 0 or (gastos_reales or 0.0) > 0,
        },
    }

    return render_template('cultivos/dashboard_cultivo.html', cultivo=cultivo, datos=datos, chart_data=chart_data)

@bp.route('/editar/<int:id>')
@login_required
def editar(id):
    cultivo = cultivo_de_usuario(id)
    return render_template('cultivos/editar.html', cultivo=cultivo)

@bp.route('/actualizar/<int:id>', methods=['POST'])
@login_required
def actualizar(id):
    cultivo = cultivo_de_usuario(id)

    nombre = request.form.get('nombre', '').strip()
    hectareas_raw = request.form.get('hectareas', '0').strip()
    fecha_sembrado_raw = request.form.get('fecha_sembrado', '').strip()

    if not nombre or not hectareas_raw or not fecha_sembrado_raw:
        flash("Por favor ingrese todos los campos obligatorios.", "danger")
        return redirect(url_for('cultivos.editar', id=id))

    try:
        hectareas = float(hectareas_raw)
        if hectareas <= 0:
            raise ValueError()
    except ValueError:
        flash("Las hectáreas deben ser un número mayor a cero.", "danger")
        return redirect(url_for('cultivos.editar', id=id))

    try:
        fecha_sembrado = datetime.strptime(fecha_sembrado_raw, '%Y-%m-%d').date()
    except ValueError:
        flash("Fecha de sembrado inválida.", "danger")
        return redirect(url_for('cultivos.editar', id=id))

    cultivo.nombre = nombre
    cultivo.hectareas = hectareas
    cultivo.fecha_sembrado = fecha_sembrado
    # Igual que al crear el cultivo: si el usuario escribió su propia
    # cantidad de plantas, esa es la que se guarda. Solo se recalcula el
    # estimado automático (~680 por hectárea) si el campo llega vacío o
    # con un valor inválido.
    plantas_raw = request.form.get('plantas', '').strip()
    try:
        plantas = int(float(plantas_raw))
        if plantas < 0:
            raise ValueError()
    except ValueError:
        plantas = int(hectareas * 680)
    cultivo.plantas = plantas

    db.session.commit()

    flash(f"¡Cultivo '{nombre}' actualizado exitosamente!", "success")
    return redirect(url_for('cultivos.index'))

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    cultivo = cultivo_de_usuario(id)
    nombre = cultivo.nombre

    # Se borran primero todos los registros que dependen de este cultivo
    # (ingresos/cosechas, gastos y actividades del calendario). Si no se
    # hace esto, esos registros quedan "huérfanos" en la base de datos y,
    # como SQLite reutiliza el mismo idCultivo para el próximo cultivo que
    # se cree, ese cultivo nuevo terminaba heredando por error la plata y
    # las etiquetas del que ya se había eliminado.
    IngresoCultivo.query.filter_by(idCultivo=id).delete()
    GastoCultivo.query.filter_by(idCultivo=id).delete()
    ActividadCultivo.query.filter_by(idCultivo=id).delete()

    db.session.delete(cultivo)
    db.session.commit()
    flash(f"El cultivo '{nombre}' y todos sus registros asociados han sido eliminados.", "info")
    return redirect(url_for('cultivos.index'))
