from app import db
from datetime import datetime

# Categorías de gasto, alineadas con las que ya se usan en el Dashboard
# (gráfica "Gastos vs. Inversión & Utilidad") para mantener el mismo lenguaje
# en toda la aplicación.
TIPOS_GASTO = {
    'insumos': {'label': 'Insumos & Fertilizantes', 'icon': 'bi-droplet-fill', 'color': '#ff4d4d'},
    'mano_obra': {'label': 'Mano de Obra (Jornales)', 'icon': 'bi-people-fill', 'color': '#ffb703'},
    'transporte': {'label': 'Transporte & Logística', 'icon': 'bi-truck', 'color': '#4cc9f0'},
    'otro': {'label': 'Otro Gasto', 'icon': 'bi-three-dots', 'color': '#b5179e'},
}


class GastoCultivo(db.Model):
    __tablename__ = 'gastos_cultivo'
    idGasto = db.Column(db.Integer, primary_key=True)
    idCultivo = db.Column(db.Integer, db.ForeignKey('cultivos.idCultivo'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.String(200), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        info = TIPOS_GASTO.get(self.tipo, {'label': self.tipo, 'icon': 'bi-cash', 'color': '#ffffff'})
        return {
            'id': self.idGasto,
            'tipo': self.tipo,
            'label': info['label'],
            'icon': info['icon'],
            'color': info['color'],
            'descripcion': self.descripcion,
            'valor': self.valor,
            'fecha': self.fecha,
        }
