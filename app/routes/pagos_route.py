from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime, date
from app.models.cultivo import Cultivo
from app.models.ingreso import IngresoCultivo, TIPOS_INGRESO
from app import db

bp = Blueprint('pagos', __name__, url_prefix='/pagos')


def _formato_moneda(valor):
    """Da formato de moneda colombiana: separador de miles con punto, sin decimales."""
    return f"{valor:,.0f}".replace(',', '.')


@bp.route('/')
@login_required
def index():
    """
    Por cada cultivo, compara el valor total de las cosechas que ya se han
    registrado (lo que se le debe pagar) contra lo que realmente le han
    pagado hasta ahora, para ver de un vistazo cuáles cultivos tienen
    cosechas pendientes de pago.
    """
    cultivos = Cultivo.query.order_by(Cultivo.idCultivo.desc()).all()

    filas = []
    total_esperado = 0.0
    total_recibido = 0.0

    for c in cultivos:
        cosechas = IngresoCultivo.query.filter_by(idCultivo=c.idCultivo).all()
        num_cosechas = len(cosechas)
        esperado = sum(x.valor for x in cosechas)
        recibido = sum((x.monto_pagado or 0.0) for x in cosechas)
        pendiente = max(esperado - recibido, 0.0)

        if num_cosechas == 0:
            estado = 'sin_cosechas'
        elif pendiente <= 0:
            estado = 'completo'
        else:
            estado = 'pendiente'

        porcentaje = round(min((recibido / esperado) * 100, 100), 1) if esperado > 0 else 0.0

        filas.append({
            'id': c.idCultivo,
            'nombre': c.nombre,
            'fecha_sembrado': c.fecha_sembrado,
            'num_cosechas': num_cosechas,
            'esperado': esperado,
            'esperado_fmt': _formato_moneda(esperado),
            'recibido': recibido,
            'recibido_fmt': _formato_moneda(recibido),
            'pendiente': pendiente,
            'pendiente_fmt': _formato_moneda(pendiente),
            'estado': estado,
            'porcentaje': porcentaje,
        })

        total_esperado += esperado
        total_recibido += recibido

    total_pendiente = max(total_esperado - total_recibido, 0.0)

    return render_template(
        'pagos/index.html',
        filas=filas,
        total_esperado=total_esperado,
        total_recibido=total_recibido,
        total_pendiente=total_pendiente,
        total_esperado_fmt=_formato_moneda(total_esperado),
        total_recibido_fmt=_formato_moneda(total_recibido),
        total_pendiente_fmt=_formato_moneda(total_pendiente),
    )


@bp.route('/cultivo/<int:id>')
@login_required
def ver(id):
    """
    Muestra, cosecha por cosecha, cuáles ya están pagas (con fecha y monto)
    y cuáles siguen pendientes de pago para este cultivo.
    """
    cultivo = Cultivo.query.get_or_404(id)
    cosechas = IngresoCultivo.query.filter_by(idCultivo=id).order_by(
        IngresoCultivo.fecha.asc(), IngresoCultivo.idIngreso.asc()
    ).all()

    filas = []
    esperado = 0.0
    recibido = 0.0

    for x in cosechas:
        info = TIPOS_INGRESO.get(x.tipo, {'label': x.tipo, 'icon': 'bi-cash', 'color': '#ffffff'})
        pagado = x.monto_pagado or 0.0
        saldo = max(x.valor - pagado, 0.0)
        esperado += x.valor
        recibido += pagado

        filas.append({
            'id': x.idIngreso,
            'tipo': x.tipo,
            'label': info['label'],
            'icon': info['icon'],
            'color': info['color'],
            'cantidad_canastillas': x.cantidad_canastillas,
            'precio_canastilla_fmt': _formato_moneda(x.precio_canastilla) if x.precio_canastilla else None,
            'descripcion': x.descripcion,
            'fecha': x.fecha,
            'valor': x.valor,
            'valor_fmt': _formato_moneda(x.valor),
            'pagado': pagado,
            'pagado_fmt': _formato_moneda(pagado),
            'saldo': saldo,
            'saldo_fmt': _formato_moneda(saldo),
            'esta_pagada': saldo <= 0,
            'fecha_pago': x.fecha_pago,
        })

    # Primero las cosechas que aún deben plata (lo más urgente de ver),
    # después las que ya quedaron completamente pagas.
    filas.sort(key=lambda f: (f['esta_pagada'], f['fecha']))

    pendiente = max(esperado - recibido, 0.0)

    return render_template(
        'pagos/ver.html',
        cultivo=cultivo,
        filas=filas,
        esperado_fmt=_formato_moneda(esperado),
        recibido_fmt=_formato_moneda(recibido),
        pendiente_fmt=_formato_moneda(pendiente),
        hay_pendientes=pendiente > 0,
    )


@bp.route('/cultivo/<int:id>/pagar', methods=['POST'])
@login_required
def registrar_pago(id):
    """
    Registra un pago recibido para este cultivo y lo reparte entre las
    cosechas pendientes, empezando por la más antigua. Si el pago alcanza
    y sobra dinero, el sobrante se abona automáticamente a la siguiente
    cosecha pendiente (y así sucesivamente).
    """
    Cultivo.query.get_or_404(id)

    try:
        monto = float(request.form.get('monto', 0) or 0)
    except ValueError:
        monto = 0.0

    fecha_str = request.form.get('fecha_pago')
    try:
        fecha_pago = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()
    except ValueError:
        fecha_pago = date.today()

    if monto <= 0:
        flash('Ingresa un monto de pago válido, mayor a $ 0.', 'danger')
        return redirect(url_for('pagos.ver', id=id))

    cosechas = IngresoCultivo.query.filter_by(idCultivo=id).order_by(
        IngresoCultivo.fecha.asc(), IngresoCultivo.idIngreso.asc()
    ).all()

    if not cosechas:
        flash('Este cultivo aún no tiene cosechas registradas. Primero registra una cosecha en Ingresos.', 'warning')
        return redirect(url_for('pagos.ver', id=id))

    restante = monto
    cosechas_cubiertas = 0

    for c in cosechas:
        saldo = c.valor - (c.monto_pagado or 0.0)
        if saldo <= 0:
            continue
        aplicar = min(saldo, restante)
        if aplicar <= 0:
            continue
        c.monto_pagado = (c.monto_pagado or 0.0) + aplicar
        c.fecha_pago = fecha_pago
        restante -= aplicar
        cosechas_cubiertas += 1
        if restante <= 0:
            break

    if restante > 0:
        # Ya no quedan cosechas pendientes: el sobrante se abona de más a la
        # última cosecha registrada, para no perder el registro del dinero.
        ultima = cosechas[-1]
        ultima.monto_pagado = (ultima.monto_pagado or 0.0) + restante
        ultima.fecha_pago = fecha_pago
        restante = 0

    db.session.commit()
    flash(
        f"Pago de $ {_formato_moneda(monto)} registrado el {fecha_pago.strftime('%d/%m/%Y')} "
        f"({cosechas_cubiertas} cosecha(s) cubierta(s)).",
        'success'
    )
    return redirect(url_for('pagos.ver', id=id))
