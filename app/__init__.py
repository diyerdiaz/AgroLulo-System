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
        return User.query.get(int(idUser))

    # Register blueprints
    from app.routes import (
        users_route, auth, users_route_async, cultivos_route, calendario_route, gastos_route, ingresos_route, pagos_route
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(users_route.bp)
    app.register_blueprint(users_route_async.bp)
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
                ('monto_pagado', 'FLOAT DEFAULT 0'),
                ('fecha_pago', 'DATE'),
            ])

            from app.models.users import User
            from app.models.cultivo import Cultivo

            if not User.query.filter_by(nameUser='admin').first():
                db.session.add(User(nameUser='admin', passwordUser='123'))
                db.session.commit()

            if Cultivo.query.count() == 0:
                lotes_defecto = [
                    Cultivo(nombre='Lote El Mirador', hectareas=4.0, plantas=2720, produccion=4200.0, ingresos=17220000.0, gastos=5650000.0),
                    Cultivo(nombre='Lote San José', hectareas=3.5, plantas=2380, produccion=3850.0, ingresos=15785000.0, gastos=5180000.0),
                    Cultivo(nombre='Lote La Esperanza', hectareas=3.0, plantas=2040, produccion=3400.0, ingresos=13940000.0, gastos=4570000.0),
                    Cultivo(nombre='Lote La Pradera', hectareas=2.0, plantas=1360, produccion=2800.0, ingresos=11505000.0, gastos=3810000.0),
                ]
                db.session.add_all(lotes_defecto)
                db.session.commit()
        except Exception as e:
            print("Auto DB init warning:", e)

    return app