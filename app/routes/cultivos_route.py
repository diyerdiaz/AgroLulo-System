from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.models.cultivo import Cultivo
from app import db
from datetime import datetime, time

bp = Blueprint('cultivos', __name__, url_prefix='/cultivos')

@bp.route('/')
@login_required
def index():
    fecha_inicio_raw = request.args.get('fecha_inicio', '').strip()
    fecha_fin_raw = request.args.get('fecha_fin', '').strip()

    query = Cultivo.query

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
    return render_template(
        'cultivos/index.html',
        cultivos=cultivos,
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

    # Cálculo proyectado proporcional a las hectáreas
    plantas = int(hectareas * 680)
    produccion = round(hectareas * 1140, 2)
    ingresos = round(hectareas * 4676000, 2)
    gastos = round(hectareas * 1536800, 2)

    nuevo_cultivo = Cultivo(
        nombre=nombre,
        hectareas=hectareas,
        fecha_sembrado=fecha_sembrado,
        plantas=plantas,
        produccion=produccion,
        ingresos=ingresos,
        gastos=gastos
    )

    db.session.add(nuevo_cultivo)
    db.session.commit()

    flash(f"¡Cultivo '{nombre}' registrado exitosamente!", "success")
    return redirect(url_for('cultivos.index'))

@bp.route('/dashboard/<int:id>')
@login_required
def dashboard(id):
    cultivo = Cultivo.query.get_or_404(id)
    datos = cultivo.to_dict()
    return render_template('cultivos/dashboard_cultivo.html', cultivo=cultivo, datos=datos)

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    cultivo = Cultivo.query.get_or_404(id)
    nombre = cultivo.nombre
    db.session.delete(cultivo)
    db.session.commit()
    flash(f"El cultivo '{nombre}' ha sido eliminado.", "info")
    return redirect(url_for('cultivos.index'))
