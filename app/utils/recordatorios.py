"""
Recordatorios del Calendario por correo, firmados por Don Pancho Lulero.

Regla del sistema: todos los días a las 6:00 a. m. (hora de Colombia) a
cada cuenta con correo le llega UN solo correo con los trabajos que tiene
anotados para ese día en el Calendario, y con los que se le pasaron y
todavía no ha marcado como hechos. El usuario no configura nada.

Los trabajos se marcan como hechos en la página (calendario o la pregunta
de Don Pancho al entrar), nunca desde el correo.

Hay 7 plantillas (temas): una por cada tipo de trabajo del calendario y
una para cuando se le pasó el día. Todas comparten el mismo diseño
(templates/correos/recordatorio.html) y cambian color, frase, consejos y
pose de Don Pancho.
"""
import os
from datetime import date
from email.utils import make_msgid

from flask import current_app, render_template, session
from flask_login import current_user

from app.models.actividad import ActividadCultivo, TIPOS_ACTIVIDAD, TIPOS_CON_SEGUIMIENTO
from app.models.cultivo import Cultivo
from app.utils.correo import enviar_correo

TEMAS = {
    'fumigacion': {
        'color': '#ff4d4d', 'fondo': '#2a0f0f', 'emoji': '💧',
        'etiqueta': 'Fumigación',
        'asunto': '💧 ¡Hoy toca fumigar, mano! · {cultivo}',
        'titulo': '¡Hoy toca', 'resaltado': 'fumigar!',
        'frase': '¡Quiubo, {nombre}! Ese lulo no se fumiga solito. Hoy hay que echarle bomba a '
                 '{cultivo} pa\' que las plagas no se lo coman. ¡No se me eche a la pereza, mano!',
        'consejos': [
            'Póngase overol, guantes, gafas y tapabocas. La salud primero, ¿oyó?',
            'No fumigue si va a llover o si está haciendo mucho viento.',
            'Ni coma ni fume mientras fumiga, y báñese bien al terminar.',
        ],
        'pose': 'senalando',
    },
    'riego': {
        'color': '#48cae4', 'fondo': '#0b2129', 'emoji': '🚿',
        'etiqueta': 'Riego',
        'asunto': '🚿 ¡Hoy toca regar, que el lulo tiene sed! · {cultivo}',
        'titulo': '¡Hoy toca', 'resaltado': 'regar!',
        'frase': '¡Ave María, {nombre}, qué sed tiene ese cultivo! Hoy le toca agüita a {cultivo}. '
                 'Planta bien regada es planta contenta. ¡Hágale pues!',
        'consejos': [
            'Riegue temprano o cuando caiga la tarde, nunca al mediodía.',
            'Échele el agua al pie de la planta, no a las hojas.',
            'Revise que no se encharque: al lulo no le gustan los pies mojados.',
        ],
        'pose': 'saludando',
    },
    'abono': {
        'color': '#b37bff', 'fondo': '#1c1030', 'emoji': '🌸',
        'etiqueta': 'Abono / Fertilización',
        'asunto': '🌸 ¡Hoy se abona! Lulo bien comido, lulo grandote · {cultivo}',
        'titulo': '¡Hoy se', 'resaltado': 'abona!',
        'frase': '¡Buenos días, {nombre}! Planta bien comida da lulo bien grande y bien pesado. '
                 'Hoy le toca su comidita a {cultivo}. ¡Qué verraquera de cosecha va a sacar!',
        'consejos': [
            'Abone con la tierra húmeda, así la planta lo aprovecha mejor.',
            'Échelo en corona, a una cuarta del tallo, no pegado a él.',
            'Anote en Gastos cuánto abono usó, pa\' saber cuánto le está costando.',
        ],
        'pose': 'senalando',
    },
    'trabajo': {
        'color': '#ffb703', 'fondo': '#2a2008', 'emoji': '🔧',
        'etiqueta': 'Trabajo / Jornal',
        'asunto': '🔧 ¡Hoy hay jornal, a madrugar! · {cultivo}',
        'titulo': '¡Hoy hay', 'resaltado': 'jornal!',
        'frase': '¡Arriba, {nombre}, que el que madruga Dios lo ayuda! Hoy se trabaja duro en '
                 '{cultivo}. ¡Hágale con toda, que esa finca no se trabaja sola!',
        'consejos': [
            'Tenga las herramientas listas y bien afiladas desde temprano.',
            'Lleve agua y algo de comer pa\' usted y pa\' los trabajadores.',
            'Anote el jornal en Gastos pa\' que no se le pierda la platica.',
        ],
        'pose': 'saludando',
    },
    'siembra': {
        'color': '#4cc9f0', 'fondo': '#0b1f29', 'emoji': '🌱',
        'etiqueta': 'Siembra',
        'asunto': '🌱 ¡Hoy se siembra! Día pa\' empezar algo grande · {cultivo}',
        'titulo': '¡Hoy se', 'resaltado': 'siembra!',
        'frase': '¡Qué día tan bonito, {nombre}! Hoy se siembra en {cultivo}, y todo lo grande '
                 'empieza con una matica. ¡Échele ganas, mano!',
        'consejos': [
            'Prepare bien el hoyo y échele abono orgánico al fondo.',
            'Respete la distancia entre plantas pa\' que no se peleen la luz.',
            'Riegue apenas termine de sembrar.',
        ],
        'pose': 'senalando',
    },
    'otro': {
        'color': '#39ff14', 'fondo': '#0f2414', 'emoji': '📋',
        'etiqueta': 'Tarea pendiente',
        'asunto': '📋 ¡Ojo, mano! Hoy tiene algo anotado · {cultivo}',
        'titulo': 'Hoy tiene algo', 'resaltado': 'pendiente',
        'frase': '¡Quiubo, {nombre}! Usted mismo dejó anotado algo pa\' hoy en {cultivo}. '
                 'No se le vaya a olvidar, ¿oyó? ¡Usted es muy verraco pa\' dejarlo pa\' mañana!',
        'consejos': [
            'Lea la nota que dejó en el calendario: ahí está lo que tiene que hacer.',
            'Cuando termine, márquelo como hecho en el calendario pa\' que le quede anotado.',
        ],
        'pose': 'pensando',
    },
    'atrasada': {
        'color': '#ff8800', 'fondo': '#2a1806', 'emoji': '⏰',
        'etiqueta': 'Se le pasó el día',
        'asunto': '⏰ ¡Ey, mano! Se le pasó un trabajo · {cultivo}',
        'titulo': '¡Se le pasó', 'resaltado': 'el día!',
        'frase': 'Uy, {nombre}, ¿qué pasó pues? Tenía trabajo anotado en {cultivo} y todavía no lo ha '
                 'marcado. Si ya lo hizo, márquelo; y si se le voló, ¡hágale hoy mismo, que todavía hay tiempo!',
        'consejos': [
            'Si ya lo hizo, entre a AgroLulo y márquelo: sirve aunque ya haya pasado el día.',
            'Si no lo hizo, muévalo en el calendario pa\' otro día.',
            'Le voy a seguir recordando hasta que lo marque. ¡Yo no me canso, mano!',
        ],
        'pose': 'pensando',
    },
}

# Si el mismo día hay varios trabajos, el correo toma el tema del más
# importante (por ejemplo, la fumigación manda sobre el riego).
PRIORIDAD = ['fumigacion', 'siembra', 'abono', 'riego', 'trabajo', 'otro']

_DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
          'septiembre', 'octubre', 'noviembre', 'diciembre']


def fecha_larga(dia):
    """date(2026, 10, 29) -> 'jueves 29 de octubre'."""
    return f'{_DIAS[dia.weekday()]} {dia.day} de {_MESES[dia.month - 1]}'


def elegir_tema(tareas_hoy, atrasadas):
    """Tema del correo: el del trabajo más importante de hoy; si hoy no hay
    nada pero sí hay trabajos atrasados, el tema 'atrasada'."""
    tipos = {t['tipo'] for t in tareas_hoy}
    for tipo in PRIORIDAD:
        if tipo in tipos:
            return tipo
    return 'atrasada' if atrasadas else 'otro'


def _preparar(tarea):
    tema = TEMAS.get(tarea['tipo'], TEMAS['otro'])
    return {**tarea, 'color': tema['color'], 'emoji': tema['emoji'], 'etiqueta': tema['etiqueta'],
            'fecha_texto': fecha_larga(tarea['fecha'])}


def armar_correo_recordatorio(nombre_usuario, tareas_hoy, atrasadas, hoy=None):
    """
    Devuelve (asunto, texto, html, imagenes) del correo del día.

    tareas_hoy / atrasadas: listas de dicts con tipo, cultivo, nota y fecha (date).
    """
    hoy = hoy or date.today()
    clave = elegir_tema(tareas_hoy, atrasadas)
    tema = TEMAS[clave]
    hoy_list = [_preparar(t) for t in tareas_hoy]
    atr_list = [_preparar(t) for t in atrasadas]

    principal = (hoy_list or atr_list)[0]
    cultivo = principal['cultivo']
    total = len(hoy_list) + len(atr_list)
    asunto = tema['asunto'].format(cultivo=cultivo)
    if total > 1:
        asunto += f' (+{total - 1} más)'

    frase = tema['frase'].format(nombre=nombre_usuario, cultivo=cultivo)

    lineas = [f'¡Quiubo, {nombre_usuario}! Aquí Don Pancho Lulero.', '',
              f'Hoy {fecha_larga(hoy)} le toca:']
    lineas += [f'  - {t["etiqueta"]} en {t["cultivo"]}' + (f': {t["nota"]}' if t['nota'] else '')
               for t in hoy_list] or ['  (nada nuevo pa\' hoy)']
    if atr_list:
        lineas += ['', 'Y esto se le quedó pendiente:']
        lineas += [f'  - {t["etiqueta"]} en {t["cultivo"]} (era pa\'l {t["fecha_texto"]})' for t in atr_list]
    lineas += ['', 'Cuando termine, entre a AgroLulo y márquelo como hecho en el Calendario.',
               '¡Hágale pues, mano!']
    texto = '\n'.join(lineas)

    cid_pancho = make_msgid(domain='agrolulo')[1:-1]
    html = render_template(
        'correos/recordatorio.html',
        tema=tema,
        nombre=nombre_usuario,
        frase=frase,
        fecha=fecha_larga(hoy),
        tareas_hoy=hoy_list,
        atrasadas=atr_list,
        anio=hoy.year,
        cid_pancho=cid_pancho,
        url_calendario=current_app.config['APP_URL'].rstrip('/') + '/calendario/',
    )
    # En JPG (no WebP) porque varios programas de correo no muestran WebP.
    ruta_pancho = os.path.join(current_app.root_path, 'static', 'img', 'don-pancho',
                               f'{tema["pose"]}.jpg')
    return asunto, texto, html, [(cid_pancho, ruta_pancho)]


def enviar_recordatorio(destino, nombre_usuario, tareas_hoy, atrasadas, hoy=None):
    asunto, texto, html, imagenes = armar_correo_recordatorio(nombre_usuario, tareas_hoy, atrasadas, hoy)
    enviar_correo(destino, asunto, texto, html, imagenes)


def ejemplos(hoy=None):
    """Los 7 correos de muestra (uno por plantilla), para verlos antes de
    activar los recordatorios: lista de (tareas_hoy, atrasadas)."""
    from datetime import timedelta
    hoy = hoy or date.today()
    def t(tipo, cultivo, nota, dias_atras=0):
        return {'tipo': tipo, 'cultivo': cultivo, 'nota': nota,
                'fecha': hoy - timedelta(days=dias_atras)}

    return [
        ([t('fumigacion', 'Lote El Mirador', 'Contra el pasador del fruto'),
          t('riego', 'Lote La Esperanza', '')], []),
        ([t('riego', 'Lote La Esperanza', 'Riego por goteo, revisar mangueras')], []),
        ([t('abono', 'Lote El Mirador', '2 bultos de 10-30-10')], []),
        ([t('trabajo', 'Lote El Mirador', 'Desyerbe y amarre de plantas · 3 jornaleros')], []),
        ([t('siembra', 'Lote Nuevo', '200 colinos de lulo castilla')], []),
        ([t('otro', 'Lote La Esperanza', 'Llevar muestra de suelo al laboratorio')], []),
        ([], [t('fumigacion', 'Lote El Mirador', 'Contra el pasador del fruto', dias_atras=1),
              t('abono', 'Lote La Esperanza', '', dias_atras=3)]),
    ]


# --- Don Pancho pregunta por los trabajos sin marcar ---
# Si la persona responde "Después le digo", no se le vuelve a preguntar
# hasta el día siguiente o hasta que vuelva a iniciar sesión.
CLAVE_POSPUESTO = 'pendientes_pospuestos'
MAXIMO_A_PREGUNTAR = 8


def actividades_pendientes(id_user, hasta=None):
    """Trabajos de la cuenta (de todos sus cultivos) con fecha de hoy o
    anterior que todavía no se han marcado como hechos, del más viejo al
    más nuevo."""
    hasta = hasta or date.today()
    return (ActividadCultivo.query
            .join(Cultivo, Cultivo.idCultivo == ActividadCultivo.idCultivo)
            .filter(Cultivo.idUser == id_user)
            .filter(ActividadCultivo.tipo.in_(TIPOS_CON_SEGUIMIENTO))
            .filter(ActividadCultivo.hecha.is_(False))
            .filter(ActividadCultivo.fecha <= hasta)
            .order_by(ActividadCultivo.fecha.asc(), ActividadCultivo.idActividad.asc())
            .all())


def hace_cuanto(fecha, hoy=None):
    """'hoy', 'ayer' o 'hace 5 días'."""
    dias = ((hoy or date.today()) - fecha).days
    if dias <= 0:
        return 'hoy'
    if dias == 1:
        return 'ayer'
    return f'hace {dias} días'


def pendientes_para_preguntar():
    """Lo que Don Pancho le pregunta a la persona al entrar (lista vacía si
    no hay nada, si no ha iniciado sesión o si dijo "Después le digo" hoy).
    Cada elemento es un dict listo para la plantilla."""
    if not current_user.is_authenticated:
        return []
    hoy = date.today()
    if session.get(CLAVE_POSPUESTO) == hoy.isoformat():
        return []
    pendientes = actividades_pendientes(current_user.idUser, hoy)[:MAXIMO_A_PREGUNTAR]
    if not pendientes:
        return []
    nombres = dict(Cultivo.query.with_entities(Cultivo.idCultivo, Cultivo.nombre)
                   .filter_by(idUser=current_user.idUser).all())
    resultado = []
    for act in pendientes:
        meta = TIPOS_ACTIVIDAD.get(act.tipo, TIPOS_ACTIVIDAD['otro'])
        resultado.append({
            'id': act.idActividad,
            'id_cultivo': act.idCultivo,
            'label': meta['label'],
            'icon': meta['icon'],
            'color': meta['color'],
            'cultivo': nombres.get(act.idCultivo, ''),
            'nota': act.nota or '',
            'cuando': hace_cuanto(act.fecha, hoy),
            'fecha': act.fecha.strftime('%d/%m/%Y'),
        })
    return resultado


def posponer_pregunta():
    session[CLAVE_POSPUESTO] = date.today().isoformat()
