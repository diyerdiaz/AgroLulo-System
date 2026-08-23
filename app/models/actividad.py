from app import db
from datetime import datetime

# Tipos de etiqueta disponibles para el calendario de un cultivo.
# 'creacion' se genera automáticamente (no aparece en el menú para agregar).
TIPOS_ACTIVIDAD = {
    'creacion':   {'label': 'Creación del Cultivo', 'icon': 'bi-flag-fill',        'color': '#39ff14'},
    'siembra':    {'label': 'Siembra',               'icon': 'bi-tree-fill',       'color': '#4cc9f0'},
    'fumigacion': {'label': 'Fumigación',            'icon': 'bi-droplet-fill',    'color': '#ff4d4d'},
    'trabajo':    {'label': 'Trabajo / Jornal',      'icon': 'bi-tools',           'color': '#ffb703'},
    'riego':      {'label': 'Riego',                 'icon': 'bi-cloud-rain-fill', 'color': '#48cae4'},
    'abono':      {'label': 'Abono / Fertilización', 'icon': 'bi-flower1',         'color': '#8338ec'},
    'cosecha':    {'label': 'Cosecha de Lulo',       'icon': 'bi-basket3-fill',    'color': '#b5179e'},
    'gasto':      {'label': 'Gasto Registrado',      'icon': 'bi-cash-coin',       'color': '#ff4d4d'},
    'pago':       {'label': 'Pago Recibido',         'icon': 'bi-patch-check-fill', 'color': '#06d6a0'},
    'otro':       {'label': 'Otro',                  'icon': 'bi-three-dots',     'color': '#9aa5a0'},
}

# Tipos que el usuario puede agregar manualmente desde el calendario
# (se excluye 'creacion', que solo se genera automáticamente).
TIPOS_SELECCIONABLES = {k: v for k, v in TIPOS_ACTIVIDAD.items() if k != 'creacion'}


class ActividadCultivo(db.Model):
    __tablename__ = 'actividades_cultivo'
    idActividad = db.Column(db.Integer, primary_key=True)
    idCultivo = db.Column(db.Integer, db.ForeignKey('cultivos.idCultivo'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    nota = db.Column(db.String(255), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    # Cuando la etiqueta se genera sola porque el usuario registró una
    # Cosecha en Ingresos, aquí queda el mismo grupo_id de esa cosecha
    # (idCogida de IngresoCultivo), para poder actualizar o borrar esta
    # etiqueta si la cosecha se edita o se elimina.
    idCogida = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        meta = TIPOS_ACTIVIDAD.get(self.tipo, TIPOS_ACTIVIDAD['otro'])
        return {
            'id': self.idActividad,
            'tipo': self.tipo,
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'nota': self.nota or '',
            'eliminable': True,
        }
