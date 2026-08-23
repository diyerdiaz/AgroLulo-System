from app import db
from datetime import datetime

# Tipos de lulo según su clasificación en cada cogida (cosecha).
# Cada tipo se paga a un precio distinto por canastilla.
TIPOS_INGRESO = {
    'grueso': {'label': 'Lulo Grueso', 'icon': 'bi-basket3-fill', 'color': '#39ff14'},
    'parejo': {'label': 'Lulo Parejo', 'icon': 'bi-basket2-fill', 'color': '#ffb703'},
    'riche': {'label': 'Lulo Riche', 'icon': 'bi-basket-fill', 'color': '#4cc9f0'},
    'otro': {'label': 'Otro Ingreso', 'icon': 'bi-three-dots', 'color': '#b5179e'},
}

# Tipos que corresponden a una clasificación de lulo por canastilla
# (el tipo "otro" es un ingreso libre, sin canastillas/precio unitario)
TIPOS_LULO_COGIDA = ['grueso', 'parejo', 'riche']


class IngresoCultivo(db.Model):
    __tablename__ = 'ingresos_cultivo'
    idIngreso = db.Column(db.Integer, primary_key=True)
    idCultivo = db.Column(db.Integer, db.ForeignKey('cultivos.idCultivo'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    cantidad_canastillas = db.Column(db.Float, nullable=True)
    precio_canastilla = db.Column(db.Float, nullable=True)
    descripcion = db.Column(db.String(200), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Seguimiento de pago de la cosecha: cuánto le han pagado ya de esta
    # cosecha en concreto y en qué fecha (puede ser parcial).
    monto_pagado = db.Column(db.Float, nullable=False, default=0.0)
    fecha_pago = db.Column(db.Date, nullable=True)

    @property
    def saldo_pendiente(self):
        return max(self.valor - (self.monto_pagado or 0.0), 0.0)

    @property
    def esta_pagada(self):
        return self.saldo_pendiente <= 0

    def to_dict(self):
        info = TIPOS_INGRESO.get(self.tipo, {'label': self.tipo, 'icon': 'bi-cash', 'color': '#ffffff'})
        return {
            'id': self.idIngreso,
            'tipo': self.tipo,
            'label': info['label'],
            'icon': info['icon'],
            'color': info['color'],
            'cantidad_canastillas': self.cantidad_canastillas,
            'precio_canastilla': self.precio_canastilla,
            'descripcion': self.descripcion,
            'valor': self.valor,
            'fecha': self.fecha,
            'monto_pagado': self.monto_pagado or 0.0,
            'fecha_pago': self.fecha_pago,
            'saldo_pendiente': self.saldo_pendiente,
            'esta_pagada': self.esta_pagada,
        }
