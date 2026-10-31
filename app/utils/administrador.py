from flask import current_app

from app import db
from app.models.users import User
from app.utils.correo import correo_valido
from app.utils.seguridad import errores_contrasena, mensaje_contrasena_invalida


def aplicar_admin_del_entorno(admin):
    """
    Le pone a la cuenta administradora los datos de ADMIN_USUARIO, ADMIN_CORREO
    y ADMIN_PASSWORD. Solo pasa una vez, mientras la cuenta siga pendiente de
    configurar: si después se cambia la contraseña desde la página, un nuevo
    despliegue no la reemplaza por la de las variables.
    """
    cfg = current_app.config
    clave = cfg.get('ADMIN_PASSWORD')
    if not clave or not admin.debe_cambiar_password:
        return

    nombre = cfg.get('ADMIN_USUARIO') or admin.nameUser
    errores = errores_contrasena(clave, nombre)
    if errores:
        print(f'ADMIN_PASSWORD no se aplicó: {mensaje_contrasena_invalida(errores)}')
        return

    if nombre != admin.nameUser and not User.query.filter_by(nameUser=nombre).first():
        admin.nameUser = nombre
    correo = (cfg.get('ADMIN_CORREO') or '').strip().lower()
    if correo_valido(correo) and not User.query.filter(
            db.func.lower(User.emailUser) == correo, User.idUser != admin.idUser).first():
        admin.emailUser = correo

    admin.set_password(clave)
    admin.debe_cambiar_password = False
    db.session.commit()
    print(f"La cuenta administradora '{admin.nameUser}' quedó lista con los datos de las variables de entorno.")
