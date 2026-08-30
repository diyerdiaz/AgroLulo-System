from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text
import os

db = SQLAlchemy()
login_manager = LoginManager()


def _asegurar_columnas(tabla, columnas):
    """
    Migración liviana para SQLite: si la tabla ya existía (creada antes de
    agregar nuevas columnas al modelo), agrega las columnas que falten sin
    borrar los datos existentes. db.create_all() no altera tablas que ya
    existen, así que esto cubre ese caso.
    columnas: lista de tuplas (nombre_columna, tipo_sql), ej: [('valor', 'FLOAT')]
    """
    existentes = [fila[1] for fila in db.session.execute(text(f'PRAGMA table_info("{tabla}")')).fetchall()]
    if not existentes:
        return  # la tabla aún no existe; db.create_all() ya se encarga de crearla completa

    for nombre_columna, tipo_sql in columnas:
        if nombre_columna not in existentes:
            db.session.execute(text(f'ALTER TABLE "{tabla}" ADD COLUMN {nombre_columna} {tipo_sql}'))

    db.session.commit()

def create_app():

    app = Flask(__name__)    
    app.config.from_object('config.Config')
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(idUser):
        from .models.users import User
        user = User.query.get(int(idUser))
        # Si al administrador le da por bloquear una cuenta que ya tenía
        # una sesión abierta, que quede afuera de una vez (no solo se le
        # impide volver a iniciar sesión).
        if user and not user.activo:
            return None
        return user

    # Register blueprints
    # NOTA: el blueprint "users_route_async" (rutas /UserAsync/...) se quitó
    # de aquí porque era una API JSON que ninguna página de AgroLulo llegó a
    # usar nunca (no había ningún botón, formulario ni script que la
    # llamara); era código muerto que no cumplía ninguna función real.
    from app.routes import (
        users_route, auth, cultivos_route, calendario_route, gastos_route, ingresos_route, pagos_route
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(users_route.bp)
    app.register_blueprint(cultivos_route.bp)
    app.register_blueprint(calendario_route.bp)
    app.register_blueprint(gastos_route.bp)
    app.register_blueprint(ingresos_route.bp)
    app.register_blueprint(pagos_route.bp)

    @app.errorhandler(Exception)
    def handle_error(e):
        print(f"An error occurred: {str(e)}")
        return {"error": str(e)}, 500

    with app.app_context():
        try:
            db.create_all()

            # Migración liviana: agrega columnas nuevas a tablas que ya
            # existían en la base de datos del usuario (creadas con una
            # versión anterior del modelo), sin perder datos.
            _asegurar_columnas('ingresos_cultivo', [
                ('cantidad_canastillas', 'FLOAT'),
                ('precio_canastilla', 'FLOAT'),
                ('peso_canastilla', 'FLOAT'),
                ('monto_pagado', 'FLOAT DEFAULT 0'),
                ('fecha_pago', 'DATE'),
                ('idCogida', 'INTEGER'),
                ('kilos_sobrantes', 'FLOAT DEFAULT 0'),
            ])
            _asegurar_columnas('actividades_cultivo', [
                ('idCogida', 'INTEGER'),
            ])
            _asegurar_columnas('users', [
                ('isAdmin', 'BOOLEAN DEFAULT 0'),
                ('activo', 'BOOLEAN DEFAULT 1'),
            ])
            _asegurar_columnas('cultivos', [
                ('idUser', 'INTEGER'),
            ])

            from app.models.users import User
            from app.models.cultivo import Cultivo

            admin = User.query.filter_by(nameUser='admin').first()
            if not admin:
                admin = User(nameUser='admin', isAdmin=True, activo=True)
                admin.set_password('123')
                db.session.add(admin)
                db.session.commit()
            else:
                cambios_admin = False
                if not admin.isAdmin:
                    # Cubre bases de datos que ya existían antes de que se
                    # agregara la columna isAdmin: la cuenta 'admin' siempre
                    # debe quedar marcada como administradora.
                    admin.isAdmin = True
                    cambios_admin = True
                if not admin.activo:
                    # La cuenta 'admin' nunca debe quedar bloqueada, aunque
                    # alguien la hubiera desactivado por error.
                    admin.activo = True
                    cambios_admin = True
                if cambios_admin:
                    db.session.commit()

            # Las contraseñas ahora se guardan encriptadas (hash), nunca en
            # texto plano. Esto encripta, sin pedirle nada a nadie, las
            # contraseñas de cuentas que ya existían de antes (guardadas tal
            # cual las escribió cada quien) apenas arranca el servidor.
            usuarios_sin_encriptar = [
                u for u in User.query.all() if not User.es_hash_valido(u.passwordUser)
            ]
            if usuarios_sin_encriptar:
                for u in usuarios_sin_encriptar:
                    u.set_password(u.passwordUser)
                db.session.commit()

            # Cada cuenta ahora ve solo sus propios cultivos. Los cultivos
            # que ya existían antes de que existiera este campo (idUser
            # vacío) se le asignan al administrador, para no perder esa
            # información: siguen siendo suyos, y las cuentas nuevas que se
            # registren de aquí en adelante arrancan sin ver nada de eso.
            huerfanos = Cultivo.query.filter_by(idUser=None).all()
            if huerfanos:
                for c in huerfanos:
                    c.idUser = admin.idUser
                db.session.commit()

            # NOTA: aquí antes se sembraban 4 cultivos de ejemplo con cifras
            # inventadas ("Lote El Mirador", etc.) cada vez que la tabla de
            # cultivos quedaba en 0 (por ejemplo, justo después de borrar
            # todos). Eso hacía que, al reiniciar el servidor con la tabla
            # vacía, reaparecieran cultivos con plata falsa como si fueran
            # reales. Se quitó: si no hay cultivos, la tabla simplemente
            # queda vacía (así lo maneja ya el Dashboard General y el
            # listado de Cultivos).
        except Exception as e:
            print("Auto DB init warning:", e)

    return app