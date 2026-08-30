from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.cultivo import Cultivo
from app.models.ingreso import IngresoCultivo, TIPOS_INGRESO, TIPOS_LULO_COGIDA
from app.models.gasto import GastoCultivo
from app.models.actividad import ActividadCultivo
from app import db
from datetime import datetime

bp = Blueprint('ingresos', __name__, url_prefix='/ingresos')


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
    total_ingresos = 0.0
    total_gastos = 0.0

    for c in cultivos:
        datos = c.to_dict()

        # Ingresos y gastos reales de este cultivo (si aún no hay ninguno,
        # queda en 0 tal como arranca un cultivo recién creado).
        ingresos_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()
        gastos_reales = db.session.query(
            db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
        ).filter(GastoCultivo.idCultivo == c.idCultivo).scalar()

        num_ingresos = IngresoCultivo.query.filter_by(idCultivo=c.idCultivo).count()

        if ingresos_reales and ingresos_reales > 0:
            datos['ingresos'] = ingresos_reales
        if gastos_reales and gastos_reales > 0:
            datos['gastos'] = gastos_reales
        datos['ganancias'] = datos['ingresos'] - datos['gastos']

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


def _grupo_de(ingreso):
    """La clave de agrupación de una cogida: su idCogida, o su propio
    idIngreso si es un registro viejo de antes de que existiera el
    agrupamiento (así cada uno queda como su propia Cosecha)."""
    return ingreso.idCogida or ingreso.idIngreso


def _filas_de_cosecha(id_cultivo, grupo_id):
    """Todos los registros (Grueso/Parejo/Riche) que pertenecen a una misma
    Cosecha dentro de un cultivo."""
    filas = IngresoCultivo.query.filter_by(idCultivo=id_cultivo, idCogida=grupo_id).all()
    if filas:
        return filas
    solo = IngresoCultivo.query.filter_by(idCultivo=id_cultivo, idIngreso=grupo_id, idCogida=None).first()
    return [solo] if solo else []


COSECHAS_POR_PAGINA = 5


def _paginar(lista, pagina_solicitada):
    """Recorta una lista ya ordenada a la página pedida (5 por página), y
    devuelve también en qué página quedó realmente y cuántas hay en total,
    para poder pintar los botones de Anterior/Siguiente."""
    total = len(lista)
    total_paginas = max(1, (total + COSECHAS_POR_PAGINA - 1) // COSECHAS_POR_PAGINA)
    pagina = max(1, min(pagina_solicitada or 1, total_paginas))
    inicio = (pagina - 1) * COSECHAS_POR_PAGINA
    return lista[inicio:inicio + COSECHAS_POR_PAGINA], pagina, total_paginas


@bp.route('/cultivo/<int:id>')
@login_required
def ver(id):
    cultivo = _cultivo_de_usuario(id)
    ingresos = IngresoCultivo.query.filter_by(idCultivo=id) \
        .order_by(IngresoCultivo.fecha.desc(), IngresoCultivo.idIngreso.desc()).all()

    # Numeramos las cosechas en orden cronológico de registro (la más
    # antigua es la Cosecha 1), aunque el listado se muestre de la más
    # reciente hacia atrás.
    numero_por_grupo = {
        grupo: idx + 1
        for idx, grupo in enumerate(sorted({_grupo_de(i) for i in ingresos}))
    }

    grupos = {}
    orden_grupos = []
    for i in ingresos:
        clave = _grupo_de(i)
        if clave not in grupos:
            grupos[clave] = []
            orden_grupos.append(clave)
        grupos[clave].append(i)

    cosechas = []
    total = 0.0
    total_kilos = 0.0
    for clave in orden_grupos:
        filas_grupo = grupos[clave]
        valor_total = sum(x.valor for x in filas_grupo)
        kilos_total = sum(x.kilos for x in filas_grupo)
        pagado_total = sum((x.monto_pagado or 0.0) for x in filas_grupo)

        orden_tipo = {t: idx for idx, t in enumerate(TIPOS_LULO_COGIDA)}
        tipos = []
        for x in sorted(filas_grupo, key=lambda r: orden_tipo.get(r.tipo, 99)):
            info = TIPOS_INGRESO.get(x.tipo, {'label': x.tipo, 'icon': 'bi-cash', 'color': '#ffffff'})
            tipos.append({
                'id': x.idIngreso,
                'tipo': x.tipo,
                'label': info['label'],
                'icon': info['icon'],
                'color': info['color'],
                'cantidad_canastillas': x.cantidad_canastillas,
                'precio_canastilla': x.precio_canastilla,
                'precio_canastilla_fmt': _formato_moneda(x.precio_canastilla) if x.precio_canastilla else None,
                'peso_canastilla': x.peso_canastilla,
                'kilos': round(x.kilos, 1),
                'kilos_sobrantes': x.kilos_sobrantes or 0.0,
                'valor_sobra': x.valor_sobra,
                'valor_sobra_fmt': _formato_moneda(x.valor_sobra) if x.valor_sobra else None,
                'tiene_sobra': bool(x.kilos_sobrantes and x.kilos_sobrantes > 0),
                'valor': x.valor,
                'valor_fmt': _formato_moneda(x.valor),
            })

        cosechas.append({
            'grupo_id': clave,
            'numero': numero_por_grupo[clave],
            'fecha': filas_grupo[0].fecha,
            'valor_total': valor_total,
            'valor_total_fmt': _formato_moneda(valor_total),
            'kilos_total': round(kilos_total, 1),
            'tipos': tipos,
            'cantidad_tipos': len(tipos),
        })
        total += valor_total
        total_kilos += kilos_total

    # Los totales de arriba ($ y Kg) siempre suman TODAS las cosechas, pero
    # la lista de abajo se recorta a 5 por página para que no crezca sin
    # límite en pantalla.
    pagina_solicitada = request.args.get('pagina', 1, type=int)
    cosechas_pagina, pagina_actual, total_paginas = _paginar(cosechas, pagina_solicitada)

    return render_template(
        'ingresos/ver.html',
        cultivo=cultivo,
        cosechas=cosechas_pagina,
        pagina_actual=pagina_actual,
        total_paginas=total_paginas,
        total=total,
        total_fmt=_formato_moneda(total),
        total_kilos=round(total_kilos, 1),
        tipos_ingreso=TIPOS_INGRESO,
    )


def _leer_kilos_sobrantes(tipo_clave):
    """Lee del formulario el check y los kilos sueltos que sobraron de un
    tipo de lulo (opcional: solo aplica si se marcó el check). Devuelve
    (kilos_sobrantes, error): error queda en None si todo está bien, o
    trae el mensaje a mostrar si el dato no es válido."""
    marcado = request.form.get(f'check_sobra_{tipo_clave}') == 'on'
    if not marcado:
        return 0.0, None

    sobra_raw = request.form.get(f'sobra_{tipo_clave}', '').strip()
    try:
        kilos_sobrantes = float(sobra_raw)
        if kilos_sobrantes <= 0:
            raise ValueError()
    except ValueError:
        etiqueta = TIPOS_INGRESO[tipo_clave]['label']
        return None, f"Revisa los kilos sueltos que sobraron de {etiqueta}: debe ser un número mayor a cero."

    return kilos_sobrantes, None


@bp.route('/cultivo/<int:id>/agregar', methods=['POST'])
@login_required
def agregar(id):
    """
    Registra una cogida: en un solo envío se pueden digitar las canastillas
    y el precio pagado de Lulo Grueso, Parejo y Riche (cada uno se paga
    diferente), más un ingreso libre "Otro" opcional. Se crea un registro
    de ingreso por cada tipo que venga con datos.
    """
    cultivo = _cultivo_de_usuario(id)

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
        peso_raw = request.form.get(f'peso_{tipo_clave}', '').strip()

        if not cantidad_raw and not precio_raw and not peso_raw:
            continue

        try:
            cantidad = float(cantidad_raw)
            precio = float(precio_raw)
            peso = float(peso_raw)
            if cantidad <= 0 or precio <= 0 or peso <= 0:
                raise ValueError()
        except ValueError:
            etiqueta = TIPOS_INGRESO[tipo_clave]['label']
            flash(f"Revisa las canastillas, el precio y el peso por canastilla de {etiqueta}: deben ser números mayores a cero.", 'danger')
            return redirect(url_for('ingresos.ver', id=id))

        kilos_sobrantes, error_sobra = _leer_kilos_sobrantes(tipo_clave)
        if error_sobra:
            flash(error_sobra, 'danger')
            return redirect(url_for('ingresos.ver', id=id))

        # Los kilos sueltos que sobraron (si los hay) se pagan al mismo
        # precio por Kg de esta canastilla: precio_canastilla / peso_canastilla.
        valor_sobra = round((precio / peso) * kilos_sobrantes, 2) if kilos_sobrantes else 0.0
        valor = round(cantidad * precio, 2) + valor_sobra
        nuevos.append(IngresoCultivo(
            idCultivo=cultivo.idCultivo,
            tipo=tipo_clave,
            cantidad_canastillas=cantidad,
            precio_canastilla=precio,
            peso_canastilla=peso,
            kilos_sobrantes=kilos_sobrantes,
            valor=valor,
            fecha=fecha,
        ))
        total_registrado += valor

    if not nuevos:
        flash('Digita las canastillas, el precio y el peso de al menos un tipo de lulo.', 'danger')
        return redirect(url_for('ingresos.ver', id=id))

    db.session.add_all(nuevos)
    db.session.flush()  # asigna los idIngreso sin cerrar la transacción todavía

    # Todos los tipos digitados en este mismo envío quedan agrupados bajo
    # una sola "Cosecha" (el id del primero de ellos), para que el listado
    # los muestre y se puedan editar/eliminar como una sola unidad.
    grupo_id = min(n.idIngreso for n in nuevos)
    for n in nuevos:
        n.idCogida = grupo_id

    # La cosecha se refleja de una vez como una etiqueta en el Calendario
    # de este cultivo, en el mismo día que se eligió al registrarla.
    total_kilos = sum(n.kilos for n in nuevos)
    db.session.add(ActividadCultivo(
        idCultivo=cultivo.idCultivo,
        idCogida=grupo_id,
        tipo='cosecha',
        fecha=fecha,
        nota=f"Cosecha registrada: {round(total_kilos, 1)} Kg por $ {_formato_moneda(total_registrado)}.",
    ))

    db.session.commit()

    flash(f"Cogida registrada: {len(nuevos)} ingreso(s) por un total de $ {_formato_moneda(total_registrado)}.", 'success')
    return redirect(url_for('ingresos.ver', id=id))


@bp.route('/cultivo/<int:id>/eliminar/<int:ingreso_id>', methods=['POST'])
@login_required
def eliminar(id, ingreso_id):
    _cultivo_de_usuario(id)
    ingreso = IngresoCultivo.query.filter_by(idIngreso=ingreso_id, idCultivo=id).first_or_404()
    db.session.delete(ingreso)
    db.session.commit()
    flash('Ingreso eliminado.', 'info')
    return redirect(url_for('ingresos.ver', id=id))


def _url_volver(origen, id):
    """A dónde regresar después de editar/eliminar una cosecha: a Ingresos
    (por defecto) o a Pagos, si fue ahí donde se inició la acción."""
    if origen == 'pagos':
        return url_for('pagos.ver', id=id)
    return url_for('ingresos.ver', id=id)


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/editar')
@login_required
def cosecha_editar(id, grupo_id):
    cultivo = _cultivo_de_usuario(id)
    origen = request.args.get('origen', 'ingresos')
    filas = _filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(_url_volver(origen, id))

    por_tipo = {x.tipo: x for x in filas}
    fecha = filas[0].fecha

    return render_template(
        'ingresos/editar_cosecha.html',
        cultivo=cultivo,
        grupo_id=grupo_id,
        fecha=fecha,
        por_tipo=por_tipo,
        tipos_ingreso=TIPOS_INGRESO,
        origen=origen,
    )


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/actualizar', methods=['POST'])
@login_required
def cosecha_actualizar(id, grupo_id):
    cultivo = _cultivo_de_usuario(id)
    origen = request.form.get('origen', 'ingresos')
    filas = _filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(_url_volver(origen, id))

    fecha_raw = request.form.get('fecha', '').strip()
    try:
        fecha = datetime.strptime(fecha_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'danger')
        return redirect(url_for('ingresos.cosecha_editar', id=id, grupo_id=grupo_id, origen=origen))

    por_tipo = {x.tipo: x for x in filas}

    # Primero se valida todo (sin tocar la base de datos) antes de aplicar
    # ningún cambio, para no dejar la cosecha a medio editar si algo falla.
    a_guardar = {}
    for tipo_clave in TIPOS_LULO_COGIDA:
        cantidad_raw = request.form.get(f'cantidad_{tipo_clave}', '').strip()
        precio_raw = request.form.get(f'precio_{tipo_clave}', '').strip()
        peso_raw = request.form.get(f'peso_{tipo_clave}', '').strip()

        if not cantidad_raw and not precio_raw and not peso_raw:
            continue

        try:
            cantidad = float(cantidad_raw)
            precio = float(precio_raw)
            peso = float(peso_raw)
            if cantidad <= 0 or precio <= 0 or peso <= 0:
                raise ValueError()
        except ValueError:
            etiqueta = TIPOS_INGRESO[tipo_clave]['label']
            flash(f"Revisa las canastillas, el precio y el peso por canastilla de {etiqueta}: deben ser números mayores a cero.", 'danger')
            return redirect(url_for('ingresos.cosecha_editar', id=id, grupo_id=grupo_id, origen=origen))

        kilos_sobrantes, error_sobra = _leer_kilos_sobrantes(tipo_clave)
        if error_sobra:
            flash(error_sobra, 'danger')
            return redirect(url_for('ingresos.cosecha_editar', id=id, grupo_id=grupo_id, origen=origen))

        a_guardar[tipo_clave] = (cantidad, precio, peso, kilos_sobrantes)

    if not a_guardar:
        flash('Debes dejar al menos un tipo de lulo con canastillas, precio y peso.', 'danger')
        return redirect(url_for('ingresos.cosecha_editar', id=id, grupo_id=grupo_id, origen=origen))

    # Los tipos que ya no vienen en el formulario se quitan de la cosecha.
    for tipo_clave, fila in list(por_tipo.items()):
        if tipo_clave not in a_guardar:
            db.session.delete(fila)

    total_actualizado = 0.0
    for tipo_clave, (cantidad, precio, peso, kilos_sobrantes) in a_guardar.items():
        valor_sobra = round((precio / peso) * kilos_sobrantes, 2) if kilos_sobrantes else 0.0
        valor = round(cantidad * precio, 2) + valor_sobra
        total_actualizado += valor
        if tipo_clave in por_tipo:
            fila = por_tipo[tipo_clave]
            fila.cantidad_canastillas = cantidad
            fila.precio_canastilla = precio
            fila.peso_canastilla = peso
            fila.kilos_sobrantes = kilos_sobrantes
            fila.valor = valor
            fila.fecha = fecha
        else:
            db.session.add(IngresoCultivo(
                idCultivo=cultivo.idCultivo,
                idCogida=grupo_id,
                tipo=tipo_clave,
                cantidad_canastillas=cantidad,
                precio_canastilla=precio,
                peso_canastilla=peso,
                kilos_sobrantes=kilos_sobrantes,
                valor=valor,
                fecha=fecha,
            ))

    # La etiqueta que esta cosecha había dejado en el Calendario se
    # actualiza igual (misma fecha nueva, mismos kilos y valor).
    total_kilos_actualizado = sum(
        cantidad * peso + (kilos_sobrantes or 0.0)
        for cantidad, precio, peso, kilos_sobrantes in a_guardar.values()
    )
    actividad = ActividadCultivo.query.filter_by(idCultivo=cultivo.idCultivo, idCogida=grupo_id, tipo='cosecha').first()
    nota_actividad = f"Cosecha registrada: {round(total_kilos_actualizado, 1)} Kg por $ {_formato_moneda(total_actualizado)}."
    if actividad:
        actividad.fecha = fecha
        actividad.nota = nota_actividad
    else:
        db.session.add(ActividadCultivo(
            idCultivo=cultivo.idCultivo,
            idCogida=grupo_id,
            tipo='cosecha',
            fecha=fecha,
            nota=nota_actividad,
        ))

    db.session.commit()
    flash(f"Cosecha actualizada: total $ {_formato_moneda(total_actualizado)}.", 'success')
    return redirect(_url_volver(origen, id))


@bp.route('/cultivo/<int:id>/cosecha/<int:grupo_id>/eliminar', methods=['POST'])
@login_required
def cosecha_eliminar(id, grupo_id):
    _cultivo_de_usuario(id)
    origen = request.form.get('origen', 'ingresos')
    filas = _filas_de_cosecha(id, grupo_id)
    if not filas:
        flash('Esa cosecha ya no existe.', 'danger')
        return redirect(_url_volver(origen, id))

    for fila in filas:
        db.session.delete(fila)

    # También se quitan las etiquetas que esa cosecha había dejado en el
    # Calendario ("Cosecha de Lulo" y, si ya le habían pagado algo, "Pago
    # Recibido"), para que no queden fantasmas.
    ActividadCultivo.query.filter_by(idCultivo=id, idCogida=grupo_id, tipo='cosecha').delete()
    ActividadCultivo.query.filter_by(idCultivo=id, idCogida=grupo_id, tipo='pago').delete()

    db.session.commit()

    flash('Cosecha eliminada.', 'info')
    return redirect(_url_volver(origen, id))
