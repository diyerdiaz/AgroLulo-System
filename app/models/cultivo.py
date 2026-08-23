from app import db
from datetime import datetime

class Cultivo(db.Model):
    __tablename__ = 'cultivos'
    idCultivo = db.Column(db.Integer, primary_key=True)
    # Dueño del cultivo: cada cuenta ve y administra únicamente los
    # cultivos (y todo lo que cuelga de ellos: ingresos, gastos, pagos,
    # calendario) que ella misma creó. Nullable porque los cultivos que ya
    # existían antes de que existiera este campo se migran aparte.
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    hectareas = db.Column(db.Float, nullable=False)
    plantas = db.Column(db.Integer, default=0)
    produccion = db.Column(db.Float, default=0.0)
    ingresos = db.Column(db.Float, default=0.0)
    gastos = db.Column(db.Float, default=0.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_sembrado = db.Column(db.Date, nullable=True)

    def to_dict(self):
        # Las plantas sí se calculan por capacidad física de la hectárea
        # (cuántas matas caben), eso no es dinero ni producción "ya lograda".
        # Producción, ingresos y gastos, en cambio, son logros reales del
        # cultivo: no se inventan a partir de las hectáreas, arrancan en 0 y
        # solo cambian cuando el usuario los registra de verdad (Ingresos,
        # Gastos, etc.).
        plantas_est = self.plantas if self.plantas > 0 else int(self.hectareas * 680)
        produccion = self.produccion or 0.0
        ingresos = self.ingresos or 0.0
        gastos = self.gastos or 0.0
        ganancias = ingresos - gastos

        return {
            "id": self.idCultivo,
            "nombre": self.nombre,
            "hectareas": self.hectareas,
            "plantas": plantas_est,
            "produccion": produccion,
            "ingresos": ingresos,
            "gastos": gastos,
            "ganancias": ganancias
        }
