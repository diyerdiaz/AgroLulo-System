from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.users import User
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app.models.ingreso import IngresoCultivo
from app.models.actividad import ActividadCultivo
from app.models.codigo_recuperacion import CodigoRecuperacion
from app.utils.panel_admin import calcular_panel, detalle_cultivador
from app.utils.correo import correo_valido, enviar_codigo_recuperacion
from app.utils.seguridad import (
    errores_contrasena, mensaje_contrasena_invalida,
    ip_solicitante, segundos_bloqueo_restante, registrar_intento_fallido, limpiar_intentos,
)
from app import db
from datetime import date, datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

bp = Blueprint('auth', __name__)

MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# Paleta de colores que se reparte entre los cultivos reales en los gráficos
# (antes el Dashboard tenía 4 cultivos y colores fijos "de mentira").
PALETA_CULTIVOS = ['#39ff14', '#4cc9f0', '#ffb703', '#b5179e', '#ff4d4d', '#06d6a0', '#8338ec', '#f72585']


# La raíz (/) es la landing page (routes/landing_route.py); el login vive en /login.
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = ip_solicitante()
        restante = segundos_bloqueo_restante(ip)
        if restante > 0:
            minutos = max(1, round(restante / 60))
            flash(f'Demasiados intentos fallidos. Intenta de nuevo en unos {minutos} minuto(s).', 'danger')
            return render_template("auth/login.html")

        nameUser = request.form['nameUser']
        passwordUser = request.form['passwordUser']

        user = User.query.filter_by(nameUser=nameUser).first()
        if user and user.check_password(passwordUser):
            if not user.activo:
                # La cuenta existe y la contraseña es correcta, pero el
                # administrador todavía no la ha activado: no se deja
                # entrar, pero tampoco se le dice "credenciales inválidas"
                # porque sí son correctas.
                flash('Tu cuenta ya fue creada, pero está esperando a que el administrador la active. Intenta iniciar sesión más tarde.', 'warning')
                return redirect(url_for('auth.login'))

            limpiar_intentos(ip)
            # Si la contraseña con la que entró no cumple las reglas de
            # seguridad actuales, también se le obliga a cambiarla.
            if errores_contrasena(passwordUser, user.nameUser) and not user.debe_cambiar_password:
                user.debe_cambiar_password = True
                db.session.commit()
            login_user(user)
            user.ultimo_acceso = datetime.utcnow()
            db.session.commit()
            if user.debe_cambiar_password:
                return redirect(url_for('auth.cambiar_contrasena'))
            flash(f"¡Bienvenido de nuevo, {user.nameUser}! Acceso concedido.", "success")
            return redirect(url_for('auth.dashboard'))

        registrar_intento_fallido(ip)
        flash('Credenciales inválidas. Usuario o contraseña incorrectos.', 'danger')
    
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template("auth/login.html")

# --- Recuperar contraseña con un código de 6 dígitos enviado al correo ---
CODIGO_MINUTOS_VALIDEZ = 15
CODIGO_INTENTOS_MAXIMOS = 5
CODIGO_SEGUNDOS_ENTRE_ENVIOS = 60
MENSAJE_CODIGO_ENVIADO = ('Listo, te enviamos un código de 6 dígitos a tu correo. '
                          'Revisa tu bandeja de entrada (y la carpeta de spam).')


def _ahora():
    """Fecha y hora actual en UTC, sin zona horaria (así se guarda en SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _buscar_cuenta(usuario_o_correo):
    """Busca la cuenta por nombre de usuario o por correo electrónico."""
    if '@' in usuario_o_correo:
        return User.query.filter(db.func.lower(User.emailUser) == usuario_o_correo.lower()).first()
    return User.query.filter_by(nameUser=usuario_o_correo).first()


@bp.route('/recuperar', methods=['POST'])
def recuperar_contrasena():
    """
    Paso 1 de "¿Olvidaste tu contraseña?": recibe el usuario o el correo y
    revisa que la cuenta exista. Si no existe (o no tiene correo para
    mandarle el código), se queda en este paso y se lo dice; si existe, le
    envía un código de 6 dígitos y pasa al paso 2.
    """
    usuario_correo = request.form.get('usuarioCorreo', '').strip()
    if not usuario_correo:
        flash('Escribe tu usuario o tu correo electrónico para recuperar la contraseña.', 'danger')
        return render_template("auth/login.html", show_recover=True)

    user = _buscar_cuenta(usuario_correo)
    if not user:
        flash('El usuario o correo no existe.', 'danger')
        return render_template("auth/login.html", show_recover=True, usuario_correo=usuario_correo)
    if not user.emailUser:
        flash('Esta cuenta no tiene un correo registrado, así que no podemos enviarle el código. '
              'Pídele al administrador que te ayude a recuperar el acceso.', 'warning')
        return render_template("auth/login.html", show_recover=True, usuario_correo=usuario_correo)

    session['recuperar_para'] = usuario_correo
    session.pop('recuperar_codigo_ok', None)

    ultimo = (CodigoRecuperacion.query.filter_by(idUser=user.idUser)
              .order_by(CodigoRecuperacion.creado.desc()).first())
    # Evita que alguien llene de correos a otra persona pidiendo códigos sin parar.
    muy_seguido = ultimo and (_ahora() - ultimo.creado).total_seconds() < CODIGO_SEGUNDOS_ENTRE_ENVIOS
    if not muy_seguido:
        codigo = f"{secrets.randbelow(10**6):06d}"
        try:
            enviar_codigo_recuperacion(user.emailUser, user.nameUser, codigo, CODIGO_MINUTOS_VALIDEZ)
        except Exception as e:
            current_app.logger.error('No se pudo enviar el código de recuperación: %s', e)
            flash('No pudimos enviar el correo en este momento. Intenta de nuevo más tarde.', 'danger')
            return render_template("auth/login.html", show_recover=True, usuario_correo=usuario_correo)

        # Solo queda vigente el código más reciente de la cuenta.
        CodigoRecuperacion.query.filter_by(idUser=user.idUser).delete()
        db.session.add(CodigoRecuperacion(
            idUser=user.idUser,
            codigo_hash=generate_password_hash(codigo, method='pbkdf2:sha256'),
            creado=_ahora(),
            expira=_ahora() + timedelta(minutes=CODIGO_MINUTOS_VALIDEZ),
            intentos=0,
        ))
        db.session.commit()

    flash(MENSAJE_CODIGO_ENVIADO, 'info')
    return render_template("auth/login.html", show_codigo=True)


@bp.route('/recuperar/codigo', methods=['POST'])
def recuperar_codigo():
    """
    Paso 2: solo revisa el código de 6 dígitos. Si es correcto, deja a la
    persona pasar al paso 3 (crear la nueva contraseña). El código vence,
    tiene un número limitado de intentos y se borra cuando se usa.
    """
    usuario_correo = session.get('recuperar_para')
    if not usuario_correo:
        flash('Primero solicita un código para recuperar tu contraseña.', 'danger')
        return render_template("auth/login.html", show_recover=True)

    codigo = request.form.get('codigo', '').strip()
    user = _buscar_cuenta(usuario_correo)
    registro = None
    if user:
        registro = (CodigoRecuperacion.query.filter_by(idUser=user.idUser)
                    .order_by(CodigoRecuperacion.creado.desc()).first())

    vigente = (registro is not None and registro.expira > _ahora()
               and registro.intentos < CODIGO_INTENTOS_MAXIMOS)
    if not vigente or not check_password_hash(registro.codigo_hash, codigo):
        if vigente:
            registro.intentos += 1
            db.session.commit()
        flash('El código es incorrecto o ya venció. Revísalo o solicita uno nuevo.', 'danger')
        return render_template("auth/login.html", show_codigo=True)

    # Código correcto: se recuerda cuál fue, para permitir el paso 3.
    session['recuperar_codigo_ok'] = registro.idCodigo
    flash('Código verificado. Ahora crea tu nueva contraseña.', 'success')
    return render_template("auth/login.html", show_nueva=True)


@bp.route('/recuperar/nueva', methods=['POST'])
def recuperar_nueva():
    """
    Paso 3: crea la nueva contraseña. Solo se llega aquí después de haber
    escrito bien el código (paso 2) y mientras ese código siga vigente.
    """
    id_codigo = session.get('recuperar_codigo_ok')
    registro = CodigoRecuperacion.query.get(id_codigo) if id_codigo else None
    if registro is None or registro.expira <= _ahora():
        session.pop('recuperar_codigo_ok', None)
        flash('Tu verificación ya venció. Solicita un código nuevo.', 'danger')
        return render_template("auth/login.html", show_recover=True)

    nueva_password = request.form.get('nueva_password', '')
    confirmar_password = request.form.get('confirmar_password', '')
    if not nueva_password:
        flash('Escribe tu nueva contraseña.', 'danger')
        return render_template("auth/login.html", show_nueva=True)
    if nueva_password != confirmar_password:
        flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
        return render_template("auth/login.html", show_nueva=True)

    user = User.query.get(registro.idUser)
    errores = errores_contrasena(nueva_password, user.nameUser)
    if errores:
        # La verificación del código sigue valiendo: solo se pide una
        # contraseña que cumpla las reglas de seguridad.
        flash(mensaje_contrasena_invalida(errores), 'danger')
        return render_template("auth/login.html", show_nueva=True)

    user.set_password(nueva_password)
    CodigoRecuperacion.query.filter_by(idUser=user.idUser).delete()
    db.session.commit()
    session.pop('recuperar_codigo_ok', None)
    session.pop('recuperar_para', None)
    flash('¡Listo! Tu contraseña se cambió. Ya puedes iniciar sesión con la nueva.', 'success')
    return redirect(url_for('auth.login'))

# Páginas a las que sí se puede entrar mientras la cuenta está obligada a
# cambiar su contraseña (todo lo demás redirige a la pantalla de cambio).
_PERMITIDAS_SIN_CAMBIAR = {'auth.cambiar_contrasena', 'auth.logout', 'static'}


@bp.before_app_request
def exigir_cambio_de_contrasena():
    """Si la cuenta que inició sesión debe cambiar su contraseña, no la deja
    usar ninguna otra página hasta que lo haga."""
    if (current_user.is_authenticated and current_user.debe_cambiar_password
            and request.endpoint not in _PERMITIDAS_SIN_CAMBIAR):
        return redirect(url_for('auth.cambiar_contrasena'))


# Secciones del cultivador. El administrador no lleva cultivos: solo
# administra cuentas y mira el panel (que no muestra cifras de nadie).
_SECCIONES_DEL_CULTIVADOR = {'cultivos', 'calendario', 'ingresos', 'gastos', 'pagos', 'analisis'}


@bp.before_app_request
def admin_fuera_de_secciones_del_cultivador():
    if (current_user.is_authenticated and current_user.isAdmin
            and request.blueprint in _SECCIONES_DEL_CULTIVADOR):
        flash('Esa sección es para los cultivadores. Como administrador, aquí tienes tu panel.', 'info')
        return redirect(url_for('auth.dashboard'))


@bp.before_app_request
def registrar_actividad():
    """Guarda cuándo fue la última vez que la cuenta usó la plataforma, a lo
    sumo cada 5 minutos (para no escribir en la base de datos en cada clic)."""
    if not current_user.is_authenticated or request.endpoint == 'static':
        return
    ahora = datetime.utcnow()
    if not current_user.ultimo_acceso or ahora - current_user.ultimo_acceso > timedelta(minutes=5):
        current_user.ultimo_acceso = ahora
        db.session.commit()


@bp.route('/cambiar-contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    """
    Pantalla obligatoria para las cuentas creadas antes de las reglas de
    seguridad: crean una contraseña nueva que cumpla las reglas y, si la
    cuenta no tiene correo, lo registran (para poder recuperarla después).
    """
    if not current_user.debe_cambiar_password:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password', '')
        confirmar_password = request.form.get('confirmar_password', '')
        correo = request.form.get('emailUser', '').strip().lower()

        if nueva_password != confirmar_password:
            flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
            return render_template('auth/cambiar_contrasena.html')
        errores = errores_contrasena(nueva_password, current_user.nameUser)
        if errores:
            flash(mensaje_contrasena_invalida(errores), 'danger')
            return render_template('auth/cambiar_contrasena.html')
        if current_user.check_password(nueva_password):
            flash('La nueva contraseña debe ser distinta a la anterior.', 'danger')
            return render_template('auth/cambiar_contrasena.html')

        if not current_user.emailUser:
            if not correo_valido(correo):
                flash('Escribe un correo electrónico válido. Lo necesitarás si olvidas tu contraseña.', 'danger')
                return render_template('auth/cambiar_contrasena.html')
            correo_en_uso = User.query.filter(
                db.func.lower(User.emailUser) == correo, User.idUser != current_user.idUser
            ).first()
            if correo_en_uso:
                flash('Ese correo ya está registrado en otra cuenta.', 'danger')
                return render_template('auth/cambiar_contrasena.html')
            current_user.emailUser = correo

        current_user.set_password(nueva_password)
        current_user.debe_cambiar_password = False
        db.session.commit()
        flash('¡Listo! Tu contraseña se actualizó. Ya puedes usar AgroLulo con normalidad.', 'success')
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/cambiar_contrasena.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """
    Arma el Dashboard General a partir de los cultivos que realmente existen
    en la base de datos. Si no hay ningún cultivo registrado, todo queda en
    cero (antes esta página tenía datos de ejemplo fijos que no cambiaban
    aunque se borraran los cultivos).
    """
    if current_user.isAdmin:
        # El administrador tiene su propio panel, minimalista y sin cifras
        # de los cultivadores (ver utils/panel_admin.py).
        return render_template('auth/dashboard_admin.html', panel=calcular_panel())

    cultivos = Cultivo.query.filter_by(idUser=current_user.idUser).order_by(Cultivo.idCultivo.desc()).all()
    total_cultivos = len(cultivos)

    total_hectareas = 0.0
    total_plantas = 0
    total_produccion = 0.0
    total_ingresos = 0.0
    total_gastos = 0.0

    nombres_cultivos = []
    produccion_por_cultivo = []
    colores_cultivos = []

    for idx, c in enumerate(cultivos):
        datos = c.to_dict()

        # Igual que en Ingresos/Gastos: si el cultivo ya tiene valores reales
        # digitados, esos mandan sobre el estimado por hectáreas.
        ingresos_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()
        gastos_reales = db.session.query(
            db.func.coalesce(db.func.sum(GastoCultivo.valor), 0.0)
        ).filter(GastoCultivo.idCultivo == c.idCultivo).scalar()
        # Producción real en Kg: canastillas x peso de cada canastilla, más
        # los kilos sueltos que hayan sobrado en cada tipo, sumado de todas
        # las cosechas registradas de verdad (Ingresos).
        produccion_reales = db.session.query(
            db.func.coalesce(db.func.sum(
                db.func.coalesce(IngresoCultivo.cantidad_canastillas * IngresoCultivo.peso_canastilla, 0.0)
                + db.func.coalesce(IngresoCultivo.kilos_sobrantes, 0.0)
            ), 0.0)
        ).filter(IngresoCultivo.idCultivo == c.idCultivo).scalar()

        ingresos_c = ingresos_reales if ingresos_reales and ingresos_reales > 0 else datos['ingresos']
        gastos_c = gastos_reales if gastos_reales and gastos_reales > 0 else datos['gastos']
        produccion_c = produccion_reales if produccion_reales and produccion_reales > 0 else datos['produccion']

        total_hectareas += c.hectareas or 0.0
        total_plantas += datos['plantas']
        total_produccion += produccion_c
        total_ingresos += ingresos_c
        total_gastos += gastos_c

        nombres_cultivos.append(c.nombre)
        produccion_por_cultivo.append(round(produccion_c, 1))
        colores_cultivos.append(PALETA_CULTIVOS[idx % len(PALETA_CULTIVOS)])

    total_ganancias = total_ingresos - total_gastos
    rentabilidad = round((total_ganancias / total_ingresos) * 100, 1) if total_ingresos > 0 else 0.0
    ha_promedio = round(total_hectareas / total_cultivos, 1) if total_cultivos > 0 else 0.0
    plantas_promedio = round(total_plantas / total_cultivos) if total_cultivos > 0 else 0

    # --- Gráfico de gastos por categoría + utilidad (solo con lo realmente
    # registrado en Gastos e Ingresos de TUS cultivos, sin mezclar con el
    # estimado ni con datos de otras cuentas) ---
    ids_cultivos_propios = [c.idCultivo for c in cultivos]
    gastos_categoria_reales = dict(
        db.session.query(GastoCultivo.tipo, db.func.sum(GastoCultivo.valor))
        .filter(GastoCultivo.idCultivo.in_(ids_cultivos_propios))
        .group_by(GastoCultivo.tipo).all()
    )
    ingresos_reales_total = db.session.query(
        db.func.coalesce(db.func.sum(IngresoCultivo.valor), 0.0)
    ).filter(IngresoCultivo.idCultivo.in_(ids_cultivos_propios)).scalar() or 0.0
    gastos_reales_total = sum(gastos_categoria_reales.values()) if gastos_categoria_reales else 0.0
    utilidad_real = ingresos_reales_total - gastos_reales_total

    pie_labels = ['Utilidad Neta (Ganancia)'] + [TIPOS_GASTO[t]['label'] for t in TIPOS_GASTO]
    pie_colores = ['#39ff14'] + [TIPOS_GASTO[t]['color'] for t in TIPOS_GASTO]
    pie_datos = [max(utilidad_real, 0.0)] + [gastos_categoria_reales.get(t, 0.0) for t in TIPOS_GASTO]
    hay_datos_pie = (ingresos_reales_total > 0) or (gastos_reales_total > 0)

    # --- Gráfico de ingresos mensuales reales por cultivo (últimos 6 meses) ---
    hoy = date.today()
    meses = []
    anio, mes = hoy.year, hoy.month
    for i in range(5, -1, -1):
        mm = mes - i
        yy = anio
        while mm <= 0:
            mm += 12
            yy -= 1
        meses.append((yy, mm))
    meses_labels = [f"{MESES_ES[mm - 1]} {yy}" for yy, mm in meses]

    series_ingresos = []
    hay_datos_linea = False
    if cultivos:
        registros = IngresoCultivo.query.filter(
            IngresoCultivo.idCultivo.in_([c.idCultivo for c in cultivos])
        ).all()
        for idx, c in enumerate(cultivos):
            por_mes = {clave: 0.0 for clave in meses}
            for r in registros:
                if r.idCultivo != c.idCultivo or not r.fecha:
                    continue
                clave = (r.fecha.year, r.fecha.month)
                if clave in por_mes:
                    por_mes[clave] += r.valor
                    hay_datos_linea = True
            series_ingresos.append({
                'label': c.nombre,
                'color': colores_cultivos[idx],
                'data': [round(por_mes[clave], 2) for clave in meses],
            })

    chart_data = {
        'produccion': {'labels': nombres_cultivos, 'data': produccion_por_cultivo, 'colores': colores_cultivos},
        'pie': {'labels': pie_labels, 'data': pie_datos, 'colores': pie_colores, 'hay_datos': hay_datos_pie},
        'linea': {'labels': meses_labels, 'series': series_ingresos, 'hay_datos': hay_datos_linea},
    }

    return render_template(
        'auth/dashboard.html',
        total_cultivos=total_cultivos,
        total_hectareas=round(total_hectareas, 1),
        total_plantas=total_plantas,
        total_produccion=round(total_produccion, 1),
        total_ingresos=round(total_ingresos, 2),
        total_gastos=round(total_gastos, 2),
        total_ganancias=round(total_ganancias, 2),
        rentabilidad=rentabilidad,
        ha_promedio=ha_promedio,
        plantas_promedio=plantas_promedio,
        chart_data=chart_data,
    )


@bp.route('/tutorial/visto', methods=['POST'])
@login_required
def tutorial_visto():
    """Lo llama Don Pancho (static/js/don-pancho.js) cuando la persona termina
    el recorrido o le da "Saltar", para que no le vuelva a salir solo."""
    if not current_user.tutorial_visto:
        current_user.tutorial_visto = True
        db.session.commit()
    return '', 204


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    """Permite a la cuenta que inició sesión cambiar su propio nombre de
    usuario y/o su contraseña. Se llega aquí al espichar el nombre de
    usuario en la barra lateral, al lado de 'Cerrar Sesión'."""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '')
        nuevo_nombre = request.form.get('nameUser', '').strip()
        nuevo_correo = request.form.get('emailUser', '').strip().lower()
        nueva_password = request.form.get('nueva_password', '')
        confirmar_password = request.form.get('confirmar_password', '')

        if not current_user.check_password(password_actual):
            flash('La contraseña actual que escribiste no es correcta.', 'danger')
            return redirect(url_for('auth.editar_perfil'))

        if not nuevo_nombre:
            flash('El nombre de usuario no puede quedar vacío.', 'danger')
            return redirect(url_for('auth.editar_perfil'))

        if nuevo_nombre != current_user.nameUser:
            ya_existe = User.query.filter(
                User.nameUser == nuevo_nombre, User.idUser != current_user.idUser
            ).first()
            if ya_existe:
                flash(f"El usuario '{nuevo_nombre}' ya está en uso por otra cuenta.", 'danger')
                return redirect(url_for('auth.editar_perfil'))

        # El correo es opcional, pero si se escribe debe ser válido y no
        # puede estar registrado en otra cuenta (se usa para recuperar la
        # contraseña con un código).
        if nuevo_correo:
            if not correo_valido(nuevo_correo):
                flash('El correo electrónico no es válido.', 'danger')
                return redirect(url_for('auth.editar_perfil'))
            correo_en_uso = User.query.filter(
                db.func.lower(User.emailUser) == nuevo_correo, User.idUser != current_user.idUser
            ).first()
            if correo_en_uso:
                flash('Ese correo ya está registrado en otra cuenta.', 'danger')
                return redirect(url_for('auth.editar_perfil'))

        if nueva_password or confirmar_password:
            if nueva_password != confirmar_password:
                flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
                return redirect(url_for('auth.editar_perfil'))
            errores = errores_contrasena(nueva_password, nuevo_nombre)
            if errores:
                flash(mensaje_contrasena_invalida(errores), 'danger')
                return redirect(url_for('auth.editar_perfil'))
            current_user.set_password(nueva_password)

        current_user.nameUser = nuevo_nombre
        current_user.emailUser = nuevo_correo or None
        db.session.commit()
        flash('Tus datos se actualizaron correctamente.', 'success')
        return redirect(url_for('auth.editar_perfil'))

    return render_template('auth/editar_perfil.html')


@bp.route('/usuarios')
@login_required
def usuarios():
    """Lista todas las cuentas registradas en el sistema (nombre de usuario
    y si es administrador o no). Solo la cuenta administradora puede verla."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede ver esa sección.', 'danger')
        return redirect(url_for('auth.dashboard'))

    usuarios = User.query.order_by(User.idUser.asc()).all()
    pagina_solicitada = request.args.get('pagina', 1, type=int)
    usuarios_pagina, pagina_actual, total_paginas = _paginar_usuarios(
        usuarios, pagina_solicitada, USUARIOS_LISTA_POR_PAGINA
    )
    return render_template(
        'auth/usuarios.html',
        usuarios=usuarios_pagina,
        total_usuarios=len(usuarios),
        pagina_actual=pagina_actual,
        total_paginas=total_paginas,
    )


@bp.route('/usuarios/crear', methods=['POST'])
@login_required
def usuario_crear():
    """Crea una cuenta nueva directamente desde el panel de Usuarios.
    A diferencia del registro público (que deja la cuenta bloqueada
    esperando activación), esta cuenta la crea el propio administrador,
    así que queda activa de inmediato. Solo el administrador puede
    hacerlo."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede crear cuentas.', 'danger')
        return redirect(url_for('auth.dashboard'))

    nameUser = request.form.get('nameUser', '').strip()
    passwordUser = request.form.get('passwordUser', '')
    emailUser = request.form.get('emailUser', '').strip().lower()

    if not nameUser or not passwordUser:
        flash('Debes escribir un nombre de usuario y una contraseña para crear la cuenta.', 'danger')
        return redirect(url_for('auth.usuarios'))

    ya_existe = User.query.filter_by(nameUser=nameUser).first()
    if ya_existe:
        flash(f"Ya existe una cuenta con el nombre de usuario '{nameUser}'.", 'danger')
        return redirect(url_for('auth.usuarios'))

    if not correo_valido(emailUser):
        flash('Escribe un correo electrónico válido para la cuenta (sirve para recuperar la contraseña).', 'danger')
        return redirect(url_for('auth.usuarios'))
    if User.query.filter(db.func.lower(User.emailUser) == emailUser).first():
        flash('Ese correo ya está registrado en otra cuenta.', 'danger')
        return redirect(url_for('auth.usuarios'))

    errores = errores_contrasena(passwordUser, nameUser)
    if errores:
        flash(mensaje_contrasena_invalida(errores), 'danger')
        return redirect(url_for('auth.usuarios'))

    nuevo_usuario = User(nameUser=nameUser, emailUser=emailUser, isAdmin=False, activo=True)
    nuevo_usuario.set_password(passwordUser)
    db.session.add(nuevo_usuario)
    db.session.commit()

    flash(f"La cuenta '{nameUser}' fue creada y ya está activa. Puede iniciar sesión de inmediato.", 'success')
    return redirect(url_for('auth.usuarios'))


# Tamaño de página para la tabla de "Usuarios Registrados": el usuario pidió
# que aparezcan los botones Anterior/Siguiente justo al llegar a 10 cuentas,
# así que con 9 por página, la cuenta número 10 ya no cabe y activa la
# paginación (mismo criterio ya usado en Estadísticas de Usuarios).
USUARIOS_LISTA_POR_PAGINA = 9

# Tamaño de página para el resumen de Estadísticas de Usuarios (se activa
# al llegar a 4 cuentas).
USUARIOS_POR_PAGINA = 3


def _paginar_usuarios(lista, pagina_solicitada, por_pagina=USUARIOS_POR_PAGINA):
    """Recorta una lista de cuentas/resúmenes a la página pedida, y
    devuelve en qué página quedó realmente y cuántas hay en total, para
    pintar los botones de Anterior/Siguiente (mismo patrón que ya se usa
    en Ingresos/Pagos) en vez de una lista larga y desordenada."""
    total = len(lista)
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    pagina = max(1, min(pagina_solicitada or 1, total_paginas))
    inicio = (pagina - 1) * por_pagina
    return lista[inicio:inicio + por_pagina], pagina, total_paginas


@bp.route('/panel/cultivador/<int:id>')
@login_required
def ficha_cultivador(id):
    """Ficha de un cultivador para el administrador: cómo ha usado la cuenta
    en cada uno de sus cultivos, en gráficos de pastel con porcentajes (sin
    ningún monto de plata). La arma utils/panel_admin.py."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede ver esa sección.', 'danger')
        return redirect(url_for('auth.dashboard'))

    usuario = User.query.get_or_404(id)
    if usuario.isAdmin:
        return redirect(url_for('auth.dashboard'))
    return render_template('auth/detalle_cultivador.html', ficha=detalle_cultivador(usuario))


@bp.route('/usuarios/estadisticas')
@login_required
def estadisticas_usuarios():
    """Antes mostraba los ingresos, gastos y ganancias de cada cultivador.
    El administrador ya no ve cifras de nadie: esta dirección ahora lleva
    al panel del administrador, que solo muestra porcentajes generales."""
    return redirect(url_for('auth.dashboard'))


@bp.route('/usuarios/<int:id>/activar', methods=['POST'])
@login_required
def usuario_activar(id):
    """Habilita una cuenta bloqueada para que ya pueda iniciar sesión.
    Solo el administrador puede hacerlo."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede activar cuentas.', 'danger')
        return redirect(url_for('auth.dashboard'))

    usuario = User.query.get_or_404(id)
    usuario.activo = True
    db.session.commit()
    flash(f"La cuenta '{usuario.nameUser}' fue activada. Ya puede iniciar sesión.", 'success')
    return redirect(url_for('auth.usuarios'))


@bp.route('/usuarios/<int:id>/bloquear', methods=['POST'])
@login_required
def usuario_bloquear(id):
    """Bloquea una cuenta para que no pueda volver a iniciar sesión hasta
    que el administrador la active de nuevo. Solo el administrador puede
    hacerlo, y no se puede bloquear a sí mismo."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede bloquear cuentas.', 'danger')
        return redirect(url_for('auth.dashboard'))

    if id == current_user.idUser:
        flash('No puedes bloquear tu propia cuenta.', 'danger')
        return redirect(url_for('auth.usuarios'))

    usuario = User.query.get_or_404(id)
    usuario.activo = False
    db.session.commit()
    flash(f"La cuenta '{usuario.nameUser}' fue bloqueada.", 'info')
    return redirect(url_for('auth.usuarios'))


@bp.route('/usuarios/<int:id>/eliminar', methods=['POST'])
@login_required
def usuario_eliminar(id):
    """Elimina por completo una cuenta y todo lo que haya registrado bajo
    ella (sus cultivos, y los ingresos, gastos, pagos y actividades del
    calendario de esos cultivos). Es irreversible. Solo el administrador
    puede hacerlo, y no se puede eliminar a sí mismo."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede eliminar cuentas.', 'danger')
        return redirect(url_for('auth.dashboard'))

    if id == current_user.idUser:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('auth.usuarios'))

    usuario = User.query.get_or_404(id)
    nombre = usuario.nameUser

    # Se borra primero todo lo que dependa de cada cultivo de esta cuenta
    # (igual que al eliminar un cultivo desde Cultivos), y luego los
    # cultivos mismos, para no dejar registros huérfanos en la base de
    # datos antes de borrar la cuenta.
    ids_cultivos = [c.idCultivo for c in Cultivo.query.filter_by(idUser=usuario.idUser).all()]
    if ids_cultivos:
        IngresoCultivo.query.filter(IngresoCultivo.idCultivo.in_(ids_cultivos)).delete(synchronize_session=False)
        GastoCultivo.query.filter(GastoCultivo.idCultivo.in_(ids_cultivos)).delete(synchronize_session=False)
        ActividadCultivo.query.filter(ActividadCultivo.idCultivo.in_(ids_cultivos)).delete(synchronize_session=False)
        Cultivo.query.filter(Cultivo.idCultivo.in_(ids_cultivos)).delete(synchronize_session=False)

    db.session.delete(usuario)
    db.session.commit()

    flash(f"La cuenta '{nombre}' y todos sus datos fueron eliminados permanentemente.", 'info')
    return redirect(url_for('auth.usuarios'))

@bp.route('/pruebajs')
def pruebajs():
    example_data = {
        'title': 'Bienvenido a Flet',
        'message': 'Este es un mensaje desde Flask.'
    }
    import json
    return json.dumps(example_data)