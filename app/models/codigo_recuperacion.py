from app import db


class CodigoRecuperacion(db.Model):
    """
    Código de 6 dígitos que se envía al correo de una cuenta cuando su dueño
    olvidó la contraseña. Nunca se guarda el código tal cual: solo su hash,
    igual que las contraseñas. Cada código vence, se puede intentar un
    número limitado de veces y se borra apenas se usa.
    """
    __tablename__ = 'codigos_recuperacion'
    idCodigo = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    codigo_hash = db.Column(db.String(255), nullable=False)
    creado = db.Column(db.DateTime, nullable=False)
    expira = db.Column(db.DateTime, nullable=False)
    intentos = db.Column(db.Integer, default=0, nullable=False)
