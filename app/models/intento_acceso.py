from app import db


class IntentoAcceso(db.Model):
    """
    Registro de acciones que se limitan para frenar ataques (ver los límites
    en utils/seguridad.py). Se guarda en la base de datos, no en memoria,
    porque Gunicorn reinicia el worker cada ~300 peticiones y eso borraría
    el bloqueo. Las filas viejas se borran solas al registrar nuevas.
    """
    __tablename__ = 'intentos_acceso'
    idIntento = db.Column(db.Integer, primary_key=True)
    accion = db.Column(db.String(20), nullable=False)
    # A quién se limita: una dirección IP, o "cuenta:<id>" para una cuenta.
    clave = db.Column(db.String(60), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)

    __table_args__ = (db.Index('ix_intentos_accion_clave_fecha', 'accion', 'clave', 'fecha'),)
