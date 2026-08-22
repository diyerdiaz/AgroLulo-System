from app import db
from datetime import datetime

class Cultivo(db.Model):
    __tablename__ = 'cultivos'
    idCultivo = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    hectareas = db.Column(db.Float, nullable=False)
    plantas = db.Column(db.Integer, default=0)
    produccion = db.Column(db.Float, default=0.0)
    ingresos = db.Column(db.Float, default=0.0)
    gastos = db.Column(db.Float, default=0.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_sembrado = db.Column(db.Date, nullable=True)

    def to_dict(self):
        plantas_est = self.plantas if self.plantas > 0 else int(self.hectareas * 680)
        prod_est = self.produccion if self.produccion > 0 else round(self.hectareas * 1140, 2)
        ing_est = self.ingresos if self.ingresos > 0 else round(self.hectareas * 4676000, 2)
        gast_est = self.gastos if self.gastos > 0 else round(self.hectareas * 1536800, 2)
        gan_est = ing_est - gast_est

        return {
            "id": self.idCultivo,
            "nombre": self.nombre,
            "hectareas": self.hectareas,
            "plantas": plantas_est,
            "produccion": prod_est,
            "ingresos": ing_est,
            "gastos": gast_est,
            "ganancias": gan_est
        }
