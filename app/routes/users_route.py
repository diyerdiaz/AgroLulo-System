from flask import Blueprint, render_template, request, redirect, url_for
from app.models.users import User
from app import db

# NOTA: este blueprint alguna vez tuvo un sistema completo de gestión de
# usuarios con listado, edición, borrado y códigos QR (rutas /User/,
# /User/edit, /User/detail, /User/delete, /User/qr, /User/read_qr). Ese
# sistema quedó de una versión anterior del proyecto y nunca estuvo
# enlazado desde ninguna página real de AgroLulo (el panel de usuarios de
# verdad, al que sí se llega desde el menú, es "Usuarios" en el sidebar,
# manejado por las rutas auth.usuarios / auth.usuario_crear / etc.). Se
# eliminó por no cumplir ninguna función visible, dejando únicamente la
# ruta 'add', que sí es la que usa de verdad el formulario "Crear Cuenta
# Nueva" del login.
bp = Blueprint('user', __name__, url_prefix='/User')

@bp.route('/add', methods=['GET', 'POST'])
def add():
    from flask import flash
    if request.method == 'POST':
        nameUser = request.form['nameUser'].strip()
        passwordUser = request.form['passwordUser']

        # El nombre de usuario debe ser único: si ya existe una cuenta con
        # ese nombre, se avisa con un mensaje claro en vez de dejar que
        # falle la base de datos (que antes tiraba un error técnico feo).
        ya_existe = User.query.filter_by(nameUser=nameUser).first()
        if ya_existe:
            flash(f"Ya existe una cuenta con el nombre de usuario '{nameUser}'. Elige otro nombre.", "danger")
            return render_template('auth/login.html', show_register=True)

        # Las cuentas que se crean desde "Crear Cuenta Nueva" quedan
        # activas de una vez, sin necesidad de que el administrador las
        # active manualmente: por eso activo=True acá.
        new_user = User(nameUser=nameUser, activo=True)
        new_user.set_password(passwordUser)
        db.session.add(new_user)
        db.session.commit()
        flash("¡Cuenta creada exitosamente! Ya puedes iniciar sesión.", "success")
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html', show_register=True)
