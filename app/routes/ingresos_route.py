from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models.cultivo import Cultivo
from app.models.ingreso import IngresoCultivo, TIPOS_INGRESO, TIPOS_LULO_COGIDA
from app import db
from datetime import datetime

bp = Blueprint('ingresos', __name__, url_prefix='/ingresos')


def _formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


@bp.route('/')
@login_required
def index():
    cultivos = Cultivo.query.order_by(Cultivo.idCultivo.desc()).all()

    filas = []
    total_ingresos = 0.0
    total_gastos = 0.0

    for c in cultivos:
        datos = c.to_dict()

        # Si el cultivo ya tiene ingresos digitados manualmente, esos son los
        # que mandan sobre el valor estimado.
        ingresos_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()

        num_ingresos = IngresoCultivo.query.filter_by(idCultivo=c.idCultivo).count()

        if ingresos_reales and ingresos_reales > 0:
            datos['ingresos'] = ingresos_reales
            datos['ganancias'] = ingresos_reales - datos['gastos']

        datos['num_ingresos'] = num_ingresos
        datos['fecha_sembrado'] = c.fecha_sembrado
        datos['gastos_fmt'] = _formato_moneda(datos['gastos'])
        datos['ingresos_fmt'] = _formato_moneda(datos['ingresos'])
        datos['ganancias_fmt'] = _formato_moneda(datos['ganancias'])
        filas.append(datos)
        total_ingresos += datos['ingresos']
        total_gastos += datos['gastos']

    total_ganancias = total_ingresos - total_gastos

    return render_template(
        'ingresos/index.html',
        filas=filas,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        total_ganancias=total_ganancias,
        total_ingresos_fmt=_formato_moneda(total_ingresos),
        total_gastos_fmt=_formato_moneda(total_gastos),
        total_ganancias_fmt=_formato_moneda(total_ganancias),
    )


@bp.route('/cultivo/<int:id>')
@login_required
def ver(id):
    cultivo = Cultivo.query.get_or_404(id)
    ingresos = IngresoCultivo.query.filter_by(idCultivo=id) \
        .order_by(IngresoCultivo.fecha.desc(), IngresoCultivo.idIngreso.desc()).all()

    filas = []
    total = 0.0
    for i in ingresos:
        f = i.to_dict()
        f['valor_fmt'] = _formato_moneda(f['valor'])
        if f['precio_canastilla']:
            f['precio_canastilla_fmt'] = _formato_moneda(f['precio_canastilla'])
        filas.append(f)
        total += f['valor']

    return render_template(
        'ingresos/ver.html',
        cultivo=cultivo,
        ingresos=filas,
        total=total,
        total_fmt=_formato_moneda(total),
        tipos_ingreso=TIPOS_INGRESO,
    )


@bp.route('/cultivo/<int:id>/agregar', methods=['POST'])
@login_required
def agregar(id):
    """
    Registra una cogida: en un solo envío se pueden digitar las canastillas
    y el precio pagado de Lulo Grueso, Parejo y Riche (cada uno se paga
    diferente), más un ingreso libre "Otro" opcional. Se crea un registro
    de ingreso por cada tipo que venga con datos.
    """
    cultivo = Cultivo.query.get_or_404(id)

    fecha_raw = request.form.get('fecha', '').strip()
    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('ingresos.ver', id=id))

    nuevos = []
    total_registrado = 0.0

    for tipo_clave in TIPOS_LULO_COGIDA:
        cantidad_raw = request.form.get(f'cantidad_{tipo_clave}', '').strip()
        precio_raw = request.form.get(f'precio_{tipo_clave}', '').strip()

        if not cantidad_raw and not precio_raw:
            continue

        try:
            cantidad = float(cantidad_raw)
            precio = float(precio_raw)
            if cantidad <= 0 or precio <= 0:
                raise ValueError()
        except ValueError:
            etiqueta = TIPOS_INGRESO[tipo_clave]['label']
            flash(f"Revisa las canastillas y el precio de {etiqueta}: deben ser números mayores a cero.", 'danger')
            return redirect(url_for('ingresos.ver', id=id))

        valor = round(cantidad * precio, 2)
        nuevos.append(IngresoCultivo(
            idCultivo=cultivo.idCultivo,
            tipo=tipo_clave,
            cantidad_canastillas=cantidad,
            precio_canastilla=precio,
            valor=valor,
            fecha=fecha,
        ))
        total_registrado += valor

    valor_otro_raw = request.form.get('valor_otro', '').strip()
    if valor_otro_raw:
        try:
            valor_otro = float(valor_otro_raw)
            if valor_otro <= 0:
                raise ValueError()
        except ValueError:
            flash('El valor de "Otro Ingreso" debe ser un número mayor a cero.', 'danger')
            return redirect(url_for('ingresos.ver', id=id))

        descripcion_otro = request.form.get('descripcion_otro', '').strip() or None
        nuevos.append(IngresoCultivo(
            idCultivo=cultivo.idCultivo,
            tipo='otro',
            valor=valor_otro,
            fecha=fecha,
            descripcion=descripcion_otro,
        ))
        total_registrado += valor_otro

    if not nuevos:
        flash('Digita al menos las canastillas y el precio de un tipo de lulo, o un Otro Ingreso.', 'danger')
        return redirect(url_for('ingresos.ver', id=id))

    db.session.add_all(nuevos)
    db.session.commit()

    flash(f"Cogida registrada: {len(nuevos)} ingreso(s) por un total de $ {_formato_moneda(total_registrado)}.", 'success')
    return redirect(url_for('ingresos.ver', id=id))


@bp.route('/cultivo/<int:id>/eliminar/<int:ingreso_id>', methods=['POST'])
@login_required
def eliminar(id, ingreso_id):
    ingreso = IngresoCultivo.query.filter_by(idIngreso=ingreso_id, idCultivo=id).first_or_404()
    db.session.delete(ingreso)
    db.session.commit()
    flash('Ingreso eliminado.', 'info')
    return redirect(url_for('ingresos.ver', id=id))
