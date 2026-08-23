from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app import db
from datetime import datetime

bp = Blueprint('gastos', __name__, url_prefix='/gastos')


def _formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


@bp.route('/')
@login_required
def index():
    cultivos = Cultivo.query.order_by(Cultivo.idCultivo.desc()).all()

    filas = []
    total_gastos = 0.0
    total_ingresos = 0.0

    for c in cultivos:
        datos = c.to_dict()

        # Si el cultivo ya tiene gastos digitados manualmente, esos son los
        # que mandan sobre el valor estimado.
        gastos_reales = db.session.query(
            db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
        ).filter(GastoCultivo.idCultivo == c.idCultivo).scalar()

        num_gastos = GastoCultivo.query.filter_by(idCultivo=c.idCultivo).count()

        if gastos_reales and gastos_reales > 0:
            datos['gastos'] = gastos_reales
            datos['ganancias'] = datos['ingresos'] - gastos_reales

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
    cultivo = Cultivo.query.get_or_404(id)
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
    cultivo = Cultivo.query.get_or_404(id)

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
    db.session.commit()

    flash(f"Gasto de $ {_formato_moneda(valor)} registrado correctamente.", 'success')
    return redirect(url_for('gastos.ver', id=id))


@bp.route('/cultivo/<int:id>/eliminar/<int:gasto_id>', methods=['POST'])
@login_required
def eliminar(id, gasto_id):
    gasto = GastoCultivo.query.filter_by(idGasto=gasto_id, idCultivo=id).first_or_404()
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto eliminado.', 'info')
    return redirect(url_for('gastos.ver', id=id))
