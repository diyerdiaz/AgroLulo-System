from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from app.models.cultivo import Cultivo
from app.models.ingreso import IngresoCultivo, TIPOS_INGRESO, TIPOS_LULO_COGIDA
from app.models.actividad import ActividadCultivo
from app.utils.helpers import formato_moneda, cultivo_de_usuario
from app.utils.cosechas import grupo_de, filas_de_cosecha, paginar
from app import db

bp = Blueprint('pagos', __name__, url_prefix='/pagos')


@bp.route('/')
@login_required
def index():
    """
    Por cada cultivo, compara el valor total de las cosechas que ya se han
    registrado (lo que se le debe pagar) contra lo que realmente le han
    pagado hasta ahora, para ver de un vistazo cuáles cultivos tienen
    cosechas pendientes de pago.
    """
    cultivos = Cultivo.query.filter_by(idUser=current_user.idUser).order_by(Cultivo.idCultivo.desc()).all()

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
            'esperado_fmt': formato_moneda(esperado),
            'recibido': recibido,
            'recibido_fmt': formato_moneda(recibido),
            'pendiente': pendiente,
            'pendiente_fmt': formato_moneda(pendiente),
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
        total_esperado_fmt=formato_moneda(total_esperado),
        total_recibido_fmt=formato_moneda(total_recibido),
        total_pendiente_fmt=formato_moneda(total_pendiente),
    )


@bp.route('/cultivo/<int:id>')
@login_required
def ver(id):
    """
    Muestra, Cosecha por Cosecha (agrupando Grueso/Parejo/Riche de una
    misma cogida en un solo registro, igual que en Ingresos), cuáles ya
    están pagas (con fecha y monto) y cuáles siguen pendientes de pago.
    """
    cultivo = cultivo_de_usuario(id)
    ingresos = IngresoCultivo.query.filter_by(idCultivo=id).order_by(
        IngresoCultivo.fecha.asc(), IngresoCultivo.idIngreso.asc()
    ).all()

    # Mismo criterio de numeración que en Ingresos, para que "Cosecha 1"
    # sea la misma cosecha en las dos pantallas.
    numero_por_grupo = {
        grupo: idx + 1
        for idx, grupo in enumerate(sorted({grupo_de(i) for i in ingresos}))
    }

    grupos = {}
    orden_grupos = []
    for i in ingresos:
        clave = grupo_de(i)
        if clave not in grupos:
            grupos[clave] = []
            orden_grupos.append(clave)
        grupos[clave].append(i)

    orden_tipo = {t: idx for idx, t in enumerate(TIPOS_LULO_COGIDA)}

    cosechas = []
    esperado = 0.0
    recibido = 0.0

    for clave in orden_grupos:
        filas_grupo = grupos[clave]
        valor_total = sum(x.valor for x in filas_grupo)
        pagado_total = sum((x.monto_pagado or 0.0) for x in filas_grupo)
        saldo_total = max(valor_total - pagado_total, 0.0)
        esta_pagada = saldo_total <= 0
        fechas_pago = [x.fecha_pago for x in filas_grupo if x.fecha_pago]
        fecha_pago = max(fechas_pago) if fechas_pago else None

        tipos = []
        for x in sorted(filas_grupo, key=lambda r: orden_tipo.get(r.tipo, 99)):
            info = TIPOS_INGRESO.get(x.tipo, {'label': x.tipo, 'icon': 'bi-cash', 'color': '#ffffff'})
            pagado = x.monto_pagado or 0.0
            saldo = max(x.valor - pagado, 0.0)
            tipos.append({
                'id': x.idIngreso,
                'tipo': x.tipo,
                'label': info['label'],
                'icon': info['icon'],
                'color': info['color'],
                'cantidad_canastillas': x.cantidad_canastillas,
                'precio_canastilla_fmt': formato_moneda(x.precio_canastilla) if x.precio_canastilla else None,
                'valor': x.valor,
                'valor_fmt': formato_moneda(x.valor),
                'pagado_fmt': formato_moneda(pagado),
                'saldo_fmt': formato_moneda(saldo),
                'esta_pagada': saldo <= 0,
            })

        cosechas.append({
            'grupo_id': clave,
            'numero': numero_por_grupo[clave],
            'fecha': filas_grupo[0].fecha,
            'cantidad_tipos': len(filas_grupo),
            'valor_total': valor_total,
            'valor_total_fmt': formato_moneda(valor_total),
            'pagado_total': pagado_total,
            'pagado_total_fmt': formato_moneda(pagado_total),
            'saldo_total': saldo_total,
            'saldo_total_fmt': formato_moneda(saldo_total),
            'esta_pagada': esta_pagada,
            'fecha_pago': fecha_pago,
            'tipos': tipos,
        })
        esperado += valor_total
        recibido += pagado_total

    # Primero las cosechas que aún deben plata (lo más urgente de ver),
    # después las que ya quedaron completamente pagas.
    cosechas.sort(key=lambda c: (c['esta_pagada'], c['fecha']))

    pendiente = max(esperado - recibido, 0.0)

    # El resumen (Esperado/Recibido/Pendiente) siempre suma TODAS las
    # cosechas; la lista de abajo se recorta a 5 por página.
    total_cosechas = len(cosechas)
    pagina_solicitada = request.args.get('pagina', 1, type=int)
    cosechas_pagina, pagina_actual, total_paginas = paginar(cosechas, pagina_solicitada)

    return render_template(
        'pagos/ver.html',
        cultivo=cultivo,
        cosechas=cosechas_pagina,
        total_cosechas=total_cosechas,
        pagina_actual=pagina_actual,
        total_paginas=total_paginas,
        esperado_fmt=formato_moneda(esperado),
        recibido_fmt=formato_moneda(recibido),
        pendiente_fmt=formato_moneda(pendiente),
        hay_pendientes=pendiente > 0,
    )


def _sincronizar_actividad_pago(id_cultivo, grupo_id):
    """Mantiene al día la etiqueta 'Pago Recibido' de una cosecha en el
    Calendario: la crea o actualiza mientras tenga algo pagado, y la quita
    si el pago queda en $ 0 (por ejemplo, al editar o eliminar el pago)."""
    filas = filas_de_cosecha(id_cultivo, grupo_id)
    actividad = ActividadCultivo.query.filter_by(
        idCultivo=id_cultivo, idCogida=grupo_id, tipo='pago'
    ).first()

    if not filas:
        if actividad:
            db.session.delete(actividad)
        return

    valor_total = sum(x.valor for x in filas)
    pagado_total = sum((x.monto_pagado or 0.0) for x in filas)
    fechas_pago = [x.fecha_pago for x in filas if x.fecha_pago]
    fecha_pago = max(fechas_pago) if fechas_pago else None

    if pagado_total <= 0 or not fecha_pago:
        if actividad:
            db.session.delete(actividad)
        return

    nota = f"Pago recibido: $ {formato_moneda(pagado_total)} de esta cosecha (valor $ {formato_moneda(valor_total)})."
    if actividad:
        actividad.fecha = fecha_pago
        actividad.nota = nota
    else:
        db.session.add(ActividadCultivo(
            idCultivo=id_cultivo,
            idCogida=grupo_id,
            tipo='pago',
            fecha=fecha_pago,
            nota=nota,
        ))


@bp.route('/cultivo/<int:id>/pagar', methods=['POST'])
@login_required
def registrar_pago(id):
    """
    Registra un pago recibido para este cultivo y lo reparte entre las
    cosechas pendientes, empezando por la más antigua. Si el pago alcanza
    y sobra dinero, el sobrante se abona automáticamente a la siguiente
    cosecha pendiente (y así sucesivamente).
    """
    cultivo_de_usuario(id)

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
    grupos_tocados = set()

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
        grupos_tocados.add(grupo_de(c))
        if restante <= 0:
            break

    if restante > 0:
        # Ya no quedan cosechas pendientes: el sobrante se abona de más a la
        # última cosecha registrada, para no perder el registro del dinero.
        ultima = cosechas[-1]
        ultima.monto_pagado = (ultima.monto_pagado or 0.0) + restante
        ultima.fecha_pago = fecha_pago
        grupos_tocados.add(grupo_de(ultima))
        restante = 0

    # Cada cosecha que recibió plata en este pago actualiza (o crea) su
    # etiqueta "Pago Recibido" en el Calendario, con el día elegido aquí.
    for grupo_id in grupos_tocados:
        _sincronizar_actividad_pago(id, grupo_id)

    db.session.commit()
    flash(
        f"Pago de $ {formato_moneda(monto)} registrado el {fecha_pago.strftime('%d/%m/%Y')} "
        f"({cosechas_cubiertas} cosecha(s) cubierta(s)).",
        'success'
    )
    return redirect(url_for('pagos.ver', id=id))


def _numero_de_cosecha(id_cultivo, grupo_id):
    """El número "Cosecha N" de un grupo, con el mismo criterio que en
    ver(), para mostrarlo también en el formulario de editar pago."""
    todos = IngresoCultivo.query.filter_by(idCultivo=id_cultivo).all()
    numero_por_grupo = {
        grupo: idx + 1
        for idx, grupo in enumerate(sorted({grupo_de(i) for i in todos}))
    }
    return numero_por_grupo.get(grupo_id, '?')


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/pago/editar')
@login_required
def pago_editar(id, grupo_id):
    """
    Corrige el monto y/o la fecha del pago ya registrado para una Cosecha
    completa (por si se digitó mal, por ejemplo con un cero de más).
    """
    cultivo = cultivo_de_usuario(id)
    filas = filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(url_for('pagos.ver', id=id))

    valor_total = sum(x.valor for x in filas)
    pagado_total = sum((x.monto_pagado or 0.0) for x in filas)
    fechas_pago = [x.fecha_pago for x in filas if x.fecha_pago]
    fecha_pago = max(fechas_pago) if fechas_pago else None

    return render_template(
        'pagos/editar_pago.html',
        cultivo=cultivo,
        grupo_id=grupo_id,
        numero=_numero_de_cosecha(id, grupo_id),
        fecha_cosecha=filas[0].fecha,
        valor_total=valor_total,
        valor_total_fmt=formato_moneda(valor_total),
        pagado_total=pagado_total,
        fecha_pago=fecha_pago,
    )


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/pago/actualizar', methods=['POST'])
@login_required
def pago_actualizar(id, grupo_id):
    cultivo_de_usuario(id)
    filas = filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(url_for('pagos.ver', id=id))

    try:
        nuevo_monto = float(request.form.get('monto', 0) or 0)
        if nuevo_monto < 0:
            raise ValueError()
    except ValueError:
        flash('El monto pagado debe ser un número mayor o igual a cero.', 'danger')
        return redirect(url_for('pagos.pago_editar', id=id, grupo_id=grupo_id))

    valor_total = sum(x.valor for x in filas)
    if nuevo_monto > valor_total:
        flash(f"El monto pagado no puede ser mayor al valor de la cosecha ($ {formato_moneda(valor_total)}).", 'danger')
        return redirect(url_for('pagos.pago_editar', id=id, grupo_id=grupo_id))

    fecha_pago = None
    if nuevo_monto > 0:
        fecha_str = request.form.get('fecha_pago', '').strip()
        try:
            fecha_pago = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()
        except ValueError:
            fecha_pago = date.today()

    # Se reparte el nuevo monto entre las filas de la cosecha empezando por
    # la más antigua, igual que el reparto automático al registrar un pago
    # nuevo, para no dejar sin sentido la fecha límite de cada tipo.
    filas_ordenadas = sorted(filas, key=lambda x: (x.fecha, x.idIngreso))
    restante = nuevo_monto
    for x in filas_ordenadas:
        aplicar = min(x.valor, restante)
        x.monto_pagado = aplicar
        x.fecha_pago = fecha_pago if aplicar > 0 else None
        restante -= aplicar

    # La etiqueta "Pago Recibido" de esta cosecha en el Calendario se
    # actualiza igual (o se quita, si el nuevo monto quedó en $ 0).
    _sincronizar_actividad_pago(id, grupo_id)

    db.session.commit()
    flash(f"Pago de la cosecha corregido a $ {formato_moneda(nuevo_monto)}.", 'success')
    return redirect(url_for('pagos.ver', id=id))


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/pago/eliminar', methods=['POST'])
@login_required
def pago_eliminar(id, grupo_id):
    """Borra el pago registrado de esta Cosecha (vuelve a quedar pendiente
    por el valor completo), sin borrar la cosecha ni sus datos de cogida."""
    cultivo_de_usuario(id)
    filas = filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(url_for('pagos.ver', id=id))

    for x in filas:
        x.monto_pagado = 0.0
        x.fecha_pago = None

    # También se quita la etiqueta "Pago Recibido" que esta cosecha tenía
    # en el Calendario, ya que vuelve a quedar sin nada pagado.
    _sincronizar_actividad_pago(id, grupo_id)

    db.session.commit()
    flash('Pago eliminado. La cosecha vuelve a quedar pendiente de pago.', 'info')
    return redirect(url_for('pagos.ver', id=id))
