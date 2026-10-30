"""
Datos imaginarios para probar AgroLulo: cultivadores con sus lotes, gastos,
cosechas, pagos y trabajos en el calendario, con cifras realistas para el
cultivo de lulo.

Todos los usuarios inventados tienen un correo que termina en
DOMINIO_DEMO, y así se pueden borrar después sin tocar los datos reales
(`flask --app run datos-demo --borrar`).
"""
import random
from datetime import date, datetime, timedelta

from app import db
from app.models.actividad import ActividadCultivo
from app.models.cultivo import Cultivo
from app.models.gasto import GastoCultivo
from app.models.ingreso import IngresoCultivo
from app.models.users import User

DOMINIO_DEMO = '@demo.agrolulo.co'

# Los nombres de usuario NO están escritos aquí: se inventan al azar cada
# vez que se corre el comando (nombre + apellido + números), así el código
# que se sube a GitHub no revela qué cuentas existen en ninguna base.
NOMBRES = ['juan', 'maria', 'pedro', 'luz', 'ramiro', 'carlos', 'ana', 'jose', 'rosa', 'hernan',
           'gloria', 'fabio', 'martha', 'alirio', 'yesenia', 'wilson', 'diana', 'oscar', 'nelly',
           'arturo', 'beatriz', 'jaime', 'olga', 'ruben', 'sandra', 'efrain', 'lucero', 'german']
APELLIDOS = ['restrepo', 'ospina', 'cardenas', 'gomez', 'quintero', 'rios', 'vargas', 'mejia',
             'pineda', 'zuluaga', 'cifuentes', 'munoz', 'toro', 'arango', 'londono', 'salazar',
             'henao', 'jaramillo', 'giraldo', 'patino', 'duque', 'valencia', 'osorio', 'betancur']
CANTIDAD_DEMO = 16
ESPERANDO_ACTIVACION = 2


def _inventar_cultivadores(r, cantidad):
    """[(usuario, activo, hace cuánto entró (None = nunca), "suerte")].
    La "suerte" (0.45 a 1.45) sube o baja las ventas: por debajo de ~0.8 el
    cultivador termina en pérdida, por encima gana."""
    usados = set()
    cultivadores = []
    while len(cultivadores) < cantidad:
        nombre = f'{r.choice(NOMBRES)}_{r.choice(APELLIDOS)}{r.randint(10, 999)}'
        if nombre in usados:
            continue
        usados.add(nombre)
        activo = len(cultivadores) >= ESPERANDO_ACTIVACION
        if not activo or r.random() < 0.08:
            hace = None
        else:
            hace = timedelta(minutes=r.randint(5, 60 * 24 * 40))
        cultivadores.append((nombre, activo, hace, round(r.uniform(0.45, 1.45), 2)))
    return cultivadores


VEREDAS = ['El Mirador', 'La Esperanza', 'Alto Bonito', 'La Cristalina', 'El Roble', 'San Isidro',
           'La Palma', 'Buenavista', 'El Diamante', 'Monteloro', 'La Florida', 'Santa Rita',
           'El Retiro', 'Las Brisas', 'Guayabal', 'La Cumbre']

NOTAS_TRABAJO = {
    'fumigacion': ['Contra el pasador del fruto', 'Control de antracnosis', 'Preventiva para gota',
                   'Contra la mosca del lulo', 'Fungicida después de las lluvias'],
    'riego': ['Riego por goteo', 'Revisar mangueras del sector alto', 'Riego de la parte nueva'],
    'abono': ['2 bultos de 10-30-10', 'Gallinaza al pie de la planta', 'Abono foliar', 'Cal dolomita'],
    'trabajo': ['Desyerbe y plateo', 'Amarre y tutorado', 'Poda de formación', 'Limpieza de canales'],
    'otro': ['Llevar muestra de suelo', 'Reunión de la asociación', 'Revisar cerca del lote'],
}
DESCRIPCION_GASTO = {
    'insumos': ['Fungicida', 'Abono 10-30-10', 'Insecticida', 'Gallinaza', 'Fertilizante foliar'],
    'mano_obra': ['Jornales de desyerbe', 'Jornales de cosecha', 'Jornales de fumigación', 'Jornal de poda'],
    'transporte': ['Flete a la plaza', 'Transporte de insumos', 'Mula para sacar la cosecha'],
    'otro': ['Canastillas nuevas', 'Repuesto de la bomba', 'Herramienta'],
}
# Precio por canastilla (pesos) y peso (Kg) de cada tipo de lulo.
PRECIOS = {'grueso': (62000, 88000), 'parejo': (40000, 58000), 'riche': (18000, 30000)}


def _plata(r, minimo, maximo, redondeo=1000):
    return round(r.uniform(minimo, maximo) / redondeo) * redondeo


def _crear_lote(r, usuario, nombre, hoy, suerte):
    hectareas = round(r.choice([0.5, 0.75, 1, 1.5, 2, 2.5, 3]), 2)
    meses = r.randint(5, 22)
    sembrado = hoy - timedelta(days=meses * 30 + r.randint(0, 25))
    lote = Cultivo(idUser=usuario.idUser, nombre=nombre, hectareas=hectareas,
                   plantas=int(hectareas * r.randint(1100, 1600)), fecha_sembrado=sembrado,
                   fecha_creacion=datetime.combine(sembrado, datetime.min.time()) + timedelta(days=2))
    db.session.add(lote)
    db.session.flush()

    # Gastos: desde la siembra, unos cada mes.
    dia = sembrado + timedelta(days=r.randint(3, 12))
    while dia <= hoy:
        for _ in range(r.randint(1, 3)):
            tipo = r.choices(['insumos', 'mano_obra', 'transporte', 'otro'], weights=[45, 35, 12, 8])[0]
            rango = {'insumos': (90000, 650000), 'mano_obra': (120000, 700000),
                     'transporte': (30000, 160000), 'otro': (25000, 220000)}[tipo]
            valor = _plata(r, *rango) * hectareas
            gasto = GastoCultivo(idCultivo=lote.idCultivo, tipo=tipo, valor=round(valor, -3),
                                 descripcion=r.choice(DESCRIPCION_GASTO[tipo]), fecha=dia,
                                 fecha_registro=datetime.combine(dia, datetime.min.time()) + timedelta(hours=18))
            db.session.add(gasto)
            db.session.flush()
            db.session.add(ActividadCultivo(idCultivo=lote.idCultivo, idCogida=gasto.idGasto, tipo='gasto',
                                            fecha=dia, nota=f'Gasto: {gasto.descripcion}'))
        dia += timedelta(days=r.randint(20, 40))

    # Cosechas: el lulo empieza a producir a los ~7 meses, cada 12-18 días.
    dia = sembrado + timedelta(days=r.randint(200, 240))
    while dia <= hoy:
        filas = []
        for tipo, (pmin, pmax) in PRECIOS.items():
            canastillas = max(1, int(r.randint(3, 14) * hectareas * suerte))
            precio = _plata(r, pmin, pmax)
            peso = r.choice([22, 24, 25, 25, 26])
            filas.append(IngresoCultivo(idCultivo=lote.idCultivo, tipo=tipo, cantidad_canastillas=canastillas,
                                        precio_canastilla=precio, peso_canastilla=peso, kilos_sobrantes=0,
                                        valor=canastillas * precio, fecha=dia,
                                        fecha_registro=datetime.combine(dia, datetime.min.time()) + timedelta(hours=17)))
        db.session.add_all(filas)
        db.session.flush()
        grupo = min(f.idIngreso for f in filas)
        for f in filas:
            f.idCogida = grupo
        kilos = sum(f.cantidad_canastillas * f.peso_canastilla for f in filas)
        db.session.add(ActividadCultivo(idCultivo=lote.idCultivo, idCogida=grupo, tipo='cosecha', fecha=dia,
                                        nota=f'Cosecha registrada: {kilos} Kg.'))
        # La mayoría de las cosechas ya se pagaron (algunas a medias).
        if (hoy - dia).days > 10 and r.random() < 0.85:
            fecha_pago = dia + timedelta(days=r.randint(3, 10))
            for f in filas:
                f.monto_pagado = f.valor if r.random() < 0.8 else round(f.valor * 0.5, -3)
                f.fecha_pago = fecha_pago
            db.session.add(ActividadCultivo(idCultivo=lote.idCultivo, idCogida=grupo, tipo='pago',
                                            fecha=fecha_pago, nota='Pago recibido de la cosecha.'))
        dia += timedelta(days=r.randint(12, 18))

    # Trabajos en el calendario: algunos pasados y algunos que vienen.
    for _ in range(r.randint(5, 14)):
        tipo = r.choices(list(NOTAS_TRABAJO), weights=[30, 20, 20, 22, 8])[0]
        fecha = hoy + timedelta(days=r.randint(-150, 20))
        if fecha < sembrado:
            continue
        db.session.add(ActividadCultivo(idCultivo=lote.idCultivo, tipo=tipo, fecha=fecha,
                                        nota=r.choice(NOTAS_TRABAJO[tipo])))
    return lote


def crear_datos_demo(clave, cantidad=CANTIDAD_DEMO):
    """Inventa `cantidad` cultivadores con sus lotes (los primeros quedan
    esperando activación). Devuelve cuántos usuarios y lotes creó."""
    r = random.SystemRandom()
    hoy = date.today()
    ahora = datetime.utcnow()
    veredas = VEREDAS[:]
    r.shuffle(veredas)
    usuarios = lotes = 0
    for i, (nombre, activo, hace, suerte) in enumerate(_inventar_cultivadores(r, cantidad)):
        if User.query.filter_by(nameUser=nombre).first():
            continue
        u = User(nameUser=nombre, emailUser=f'{nombre}{DOMINIO_DEMO}', activo=activo,
                 debe_cambiar_password=False, tutorial_visto=True,
                 ultimo_acceso=(ahora - hace) if hace else None)
        u.set_password(clave)
        db.session.add(u)
        db.session.flush()
        usuarios += 1
        if not activo:
            continue
        for j in range(r.choice([1, 1, 2, 2, 3])):
            _crear_lote(r, u, f'Lote {veredas[(i + j * 5) % len(veredas)]}', hoy, suerte)
            lotes += 1
    db.session.commit()
    return usuarios, lotes


def borrar_datos_demo():
    """Borra SOLO los usuarios imaginarios (correo con DOMINIO_DEMO) y todo lo suyo."""
    demo = User.query.filter(User.emailUser.like(f'%{DOMINIO_DEMO}')).all()
    ids_lotes = [c.idCultivo for c in Cultivo.query.filter(Cultivo.idUser.in_([u.idUser for u in demo])).all()]
    if ids_lotes:
        for modelo in (IngresoCultivo, GastoCultivo, ActividadCultivo):
            modelo.query.filter(modelo.idCultivo.in_(ids_lotes)).delete(synchronize_session=False)
        Cultivo.query.filter(Cultivo.idCultivo.in_(ids_lotes)).delete(synchronize_session=False)
    for u in demo:
        db.session.delete(u)
    db.session.commit()
    return len(demo)
