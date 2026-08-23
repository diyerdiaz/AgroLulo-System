from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.users import User
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo, TIPOS_GASTO
from app.models.ingreso import IngresoCultivo
from app import db
from datetime import date

bp = Blueprint('auth', __name__)

MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# Paleta de colores que se reparte entre los cultivos reales en los gráficos
# (antes el Dashboard tenía 4 cultivos y colores fijos "de mentira").
PALETA_CULTIVOS = ['#39ff14', '#4cc9f0', '#ffb703', '#b5179e', '#ff4d4d', '#06d6a0', '#8338ec', '#f72585']

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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

            login_user(user)
            flash(f"¡Bienvenido de nuevo, {user.nameUser}! Acceso concedido.", "success")
            return redirect(url_for('auth.dashboard'))

        flash('Credenciales inválidas. Usuario o contraseña incorrectos.', 'danger')
    
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template("login.html")

@bp.route('/dashboard')
@login_required
def dashboard():
    """
    Arma el Dashboard General a partir de los cultivos que realmente existen
    en la base de datos. Si no hay ningún cultivo registrado, todo queda en
    cero (antes esta página tenía datos de ejemplo fijos que no cambiaban
    aunque se borraran los cultivos).
    """
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
        # Producción real en Kg: canastillas x peso de cada canastilla,
        # sumado de todas las cosechas registradas de verdad (Ingresos).
        produccion_reales = db.session.query(
            db.func.coalesce(db.func.sum(IngresoCultivo.cantidad_canastillas * IngresoCultivo.peso_canastilla), 0.0)
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
        'dashboard.html',
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

        if nueva_password or confirmar_password:
            if nueva_password != confirmar_password:
                flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
                return redirect(url_for('auth.editar_perfil'))
            current_user.set_password(nueva_password)

        current_user.nameUser = nuevo_nombre
        db.session.commit()
        flash('Tus datos se actualizaron correctamente.', 'success')
        return redirect(url_for('auth.editar_perfil'))

    return render_template('editar_perfil.html')


@bp.route('/usuarios')
@login_required
def usuarios():
    """Lista todas las cuentas registradas en el sistema (nombre de usuario
    y si es administrador o no). Solo la cuenta administradora puede verla."""
    if not current_user.isAdmin:
        flash('Solo el administrador puede ver esa sección.', 'danger')
        return redirect(url_for('auth.dashboard'))

    usuarios = User.query.order_by(User.idUser.asc()).all()
    return render_template('usuarios.html', usuarios=usuarios)


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

@bp.route('/pruebajs')
def pruebajs():
    example_data = {
        'title': 'Bienvenido a Flet',
        'message': 'Este es un mensaje desde Flask.'
    }
    import json
    return json.dumps(example_data)