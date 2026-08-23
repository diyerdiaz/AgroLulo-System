from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app.models.ingreso import IngresoCultivo
from app.models.actividad import ActividadCultivo
from app import db
from datetime import datetime

bp = Blueprint('gastos', __name__, url_prefix='/gastos')


def _formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


def _cultivo_de_usuario(id):
    """Trae el cultivo por id, pero solo si es del usuario que inició
    sesión: cada cuenta ve y administra únicamente sus propios cultivos."""
    return Cultivo.query.filter_by(idCultivo=id, idUser=current_user.idUser).first_or_404()


@bp.route('/')
@login_required
def index():
    cultivos = Cultivo.query.filter_by(idUser=current_user.idUser).order_by(Cultivo.idCultivo.desc()).all()

    filas = []
    total_gastos = 0.0
    total_ingresos = 0.0

    for c in cultivos:
        datos = c.to_dict()

        # Gastos e ingresos reales de este cultivo (si aún no hay ninguno,
        # queda en 0 tal como arranca un cultivo recién creado).
        gastos_reales = db.session.query(
            db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
        ).filter(GastoCultivo.idCultivo == c.idCultivo).scalar()
        ingresos_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()

        num_gastos = GastoCultivo.query.filter_by(idCultivo=c.idCultivo).count()

        if gastos_reales and gastos_reales > 0:
            datos['gastos'] = gastos_reales
        if ingresos_reales and ingresos_reales > 0:
            datos['ingresos'] = ingresos_reales
        datos['ganancias'] = datos['ingresos'] - datos['gastos']

        datos['num_gastos'] = num_gastos
        datos['fecha_sembrado'] = c.fecha_sembrado
        datos['gastos_fmt'] = _formato_moneda(datos['gastos'])
        datos['ingresos_fmt'] = _formato_moneda(datos['ingresos'])
        datos['ganancias_fmt'] = _formato_moneda(datos['ganancias'])
        filas.append(datos)
        total_gastos += datos['gastos']
        total_ingresos += datos['ingresos']

    total_ganancias = total_ingresos - total_gastos

    return render_template(
        'gastos/index.html',
        filas=filas,
        total_gastos=total_gastos,
        total_ingresos=total_ingresos,
        total_ganancias=total_ganancias,
        total_gastos_fmt=_formato_moneda(total_gastos),
        total_ingresos_fmt=_formato_moneda(total_ingresos),
        total_ganancias_fmt=_formato_moneda(total_ganancias),
    )


@bp.route('/cultivo/<int:id>')
@login_required
def ver(id):
    cultivo = _cultivo_de_usuario(id)
    gastos = GastoCultivo.query.filter_by(idCultivo=id) \
        .order_by(GastoCultivo.fecha.desc(), GastoCultivo.idGasto.desc()).all()

    filas = []
    total = 0.0
    for g in gastos:
        f = g.to_dict()
        f['valor_fmt'] = _formato_moneda(f['valor'])
        filas.append(f)
        total += f['valor']

    return render_template(
        'gastos/ver.html',
        cultivo=cultivo,
        gastos=filas,
        total=total,
        total_fmt=_formato_moneda(total),
        tipos_gasto=TIPOS_GASTO,
    )


@bp.route('/cultivo/<int:id>/agregar', methods=['POST'])
@login_required
def agregar(id):
    cultivo = _cultivo_de_usuario(id)

    tipo = request.form.get('tipo', '').strip()
    valor_raw = request.form.get('valor', '').strip()
    fecha_raw = request.form.get('fecha', '').strip()
    descripcion = request.form.get('descripcion', '').strip() or None

    if tipo not in TIPOS_GASTO:
        flash('Selecciona un tipo de gasto válido.', 'danger')
        return redirect(url_for('gastos.ver', id=id))

    try:
        valor = float(valor_raw)
        if valor <= 0:
            raise ValueError()
    except ValueError:
        flash('El valor del gasto debe ser un número mayor a cero.', 'danger')
        return redirect(url_for('gastos.ver', id=id))

    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('gastos.ver', id=id))

    nuevo_gasto = GastoCultivo(
        idCultivo=cultivo.idCultivo,
        tipo=tipo,
        valor=valor,
        fecha=fecha,
        descripcion=descripcion,
    )
    db.session.add(nuevo_gasto)
    db.session.flush()  # asigna el idGasto sin cerrar la transacción todavía

    # El gasto también se refleja de una vez como una etiqueta en el
    # Calendario de este cultivo, en el mismo día que se eligió al
    # registrarlo.
    nota_actividad = f"{TIPOS_GASTO[tipo]['label']}: $ {_formato_moneda(valor)}"
    if descripcion:
        nota_actividad += f" — {descripcion}"
    db.session.add(ActividadCultivo(
        idCultivo=cultivo.idCultivo,
        idCogida=nuevo_gasto.idGasto,
        tipo='gasto',
        fecha=fecha,
        nota=nota_actividad,
    ))

    db.session.commit()

    flash(f"Gasto de $ {_formato_moneda(valor)} registrado correctamente.", 'success')
    return redirect(url_for('gastos.ver', id=id))


@bp.route('/cultivo/<int:id>/gasto/<int:gasto_id>/editar')
@login_required
def editar_gasto(id, gasto_id):
    cultivo = _cultivo_de_usuario(id)
    gasto = GastoCultivo.query.filter_by(idGasto=gasto_id, idCultivo=id).first_or_404()
    return render_template('gastos/editar.html', cultivo=cultivo, gasto=gasto, tipos_gasto=TIPOS_GASTO)


@bp.route('/cultivo/<int:id>/gasto/<int:gasto_id>/actualizar', methods=['POST'])
@login_required
def actualizar_gasto(id, gasto_id):
    _cultivo_de_usuario(id)
    gasto = GastoCultivo.query.filter_by(idGasto=gasto_id, idCultivo=id).first_or_404()

    tipo = request.form.get('tipo', '').strip()
    valor_raw = request.form.get('valor', '').strip()
    fecha_raw = request.form.get('fecha', '').strip()
    descripcion = request.form.get('descripcion', '').strip() or None

    if tipo not in TIPOS_GASTO:
        flash('Selecciona un tipo de gasto válido.', 'danger')
        return redirect(url_for('gastos.editar_gasto', id=id, gasto_id=gasto_id))

    try:
        valor = float(valor_raw)
        if valor <= 0:
            raise ValueError()
    except ValueError:
        flash('El valor del gasto debe ser un número mayor a cero.', 'danger')
        return redirect(url_for('gastos.editar_gasto', id=id, gasto_id=gasto_id))

    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('gastos.editar_gasto', id=id, gasto_id=gasto_id))

    gasto.tipo = tipo
    gasto.valor = valor
    gasto.fecha = fecha
    gasto.descripcion = descripcion

    # La etiqueta que este gasto había dejado en el Calendario se
    # actualiza igual (mismo tipo, valor, descripción y fecha nuevos).
    nota_actividad = f"{TIPOS_GASTO[tipo]['label']}: $ {_formato_moneda(valor)}"
    if descripcion:
        nota_actividad += f" — {descripcion}"
    actividad = ActividadCultivo.query.filter_by(idCultivo=id, idCogida=gasto_id, tipo='gasto').first()
    if actividad:
        actividad.fecha = fecha
        actividad.nota = nota_actividad
    else:
        db.session.add(ActividadCultivo(
            idCultivo=id,
            idCogida=gasto_id,
            tipo='gasto',
            fecha=fecha,
            nota=nota_actividad,
        ))

    db.session.commit()
    flash('Gasto actualizado correctamente.', 'success')
    return redirect(url_for('gastos.ver', id=id))


@bp.route('/cultivo/<int:id>/eliminar/<int:gasto_id>', methods=['POST'])
@login_required
def eliminar(id, gasto_id):
    _cultivo_de_usuario(id)
    gasto = GastoCultivo.query.filter_by(idGasto=gasto_id, idCultivo=id).first_or_404()
    db.session.delete(gasto)

    # También se quita la etiqueta que ese gasto había dejado en el
    # Calendario, para que no quede una "Gasto Registrado" fantasma.
    ActividadCultivo.query.filter_by(idCultivo=id, idCogida=gasto_id, tipo='gasto').delete()

    db.session.commit()
    flash('Gasto eliminado.', 'info')
    return redirect(url_for('gastos.ver', id=id))
