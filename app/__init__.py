from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

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
        users_route, auth, users_route_async, cultivos_route
    )
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(users_route.bp)
    app.register_blueprint(users_route_async.bp)
    app.register_blueprint(cultivos_route.bp)

    @app.errorhandler(Exception)
    def handle_error(e):
        print(f"An error occurred: {str(e)}")
        return {"error": str(e)}, 500

    with app.app_context():
        try:
            db.create_all()
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