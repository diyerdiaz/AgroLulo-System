"""
Herramienta de Análisis: conteo estimado de "matas" (plantas) a partir de
una foto del cultivo.

Cómo funciona:
1. YOLOv8 (modelo .onnx incluido en app/ml/models/) corre como detector de
   objetos general, igual que el "YOLO" que se pidió. Como los modelos
   YOLO listos para usar vienen entrenados con fotos de la vida diaria
   (personas, carros, animales, "planta en maceta", etc.) y NO existe una
   clase entrenada específicamente para "mata de lulo en el lote", sus
   detecciones se muestran aparte, solo como información complementaria.
2. El conteo principal de matas se calcula con una técnica de visión por
   computador hecha específicamente para vegetación en fotos de campo:
   el Índice de Verde Excesivo (ExG), muy usado en agricultura para
   separar hojas/plantas del suelo o del fondo de la foto. Sobre esa
   máscara se cuentan las manchas de vegetación (cada una = una mata
   aproximada). Por tratarse de una estimación a partir de una imagen,
   el número resultante es aproximado, no un conteo exacto garantizado.
"""
import os
import uuid

import cv2
import numpy as np
import onnxruntime as ort

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'yolov8n.onnx')

YOLO_INPUT_SIZE = 640
YOLO_CONF_THRESHOLD = 0.35
YOLO_IOU_THRESHOLD = 0.45

# Las 80 clases del dataset COCO con el que viene entrenado YOLOv8 por
# defecto (ninguna es "mata de lulo": por eso estas detecciones solo se
# muestran como dato complementario, y el conteo de matas usa la técnica
# de vegetación de abajo).
COCO_CLASSES = [
    'persona', 'bicicleta', 'carro', 'moto', 'avión', 'bus', 'tren', 'camión', 'bote',
    'semáforo', 'hidrante', 'señal de pare', 'parquímetro', 'banca', 'pájaro', 'gato',
    'perro', 'caballo', 'oveja', 'vaca', 'elefante', 'oso', 'cebra', 'jirafa', 'mochila',
    'paraguas', 'bolso', 'corbata', 'maleta', 'frisbee', 'esquís', 'tabla de snowboard',
    'balón', 'cometa', 'bate de béisbol', 'guante de béisbol', 'patineta', 'tabla de surf',
    'raqueta de tenis', 'botella', 'copa de vino', 'vaso', 'tenedor', 'cuchillo', 'cuchara',
    'tazón', 'banano', 'manzana', 'sándwich', 'naranja', 'brócoli', 'zanahoria', 'perro caliente',
    'pizza', 'dona', 'torta', 'silla', 'sofá', 'planta en maceta', 'cama', 'mesa de comedor',
    'inodoro', 'televisor', 'portátil', 'mouse', 'control remoto', 'teclado', 'celular',
    'microondas', 'horno', 'tostadora', 'lavaplatos', 'nevera', 'libro', 'reloj', 'florero',
    'tijeras', 'oso de peluche', 'secador de pelo', 'cepillo de dientes',
]


_sesion_yolo = None


def _cargar_sesion_yolo():
    """Carga el modelo YOLOv8 (.onnx) una sola vez y lo reutiliza en las
    siguientes fotos (cargarlo desde disco toma un par de segundos)."""
    global _sesion_yolo
    if _sesion_yolo is None:
        _sesion_yolo = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    return _sesion_yolo


def _preprocesar_para_yolo(imagen_bgr):
    """Redimensiona la foto a 640x640 (con relleno tipo "letterbox" para no
    deformarla) y la normaliza como espera el modelo."""
    alto0, ancho0 = imagen_bgr.shape[:2]
    escala = min(YOLO_INPUT_SIZE / alto0, YOLO_INPUT_SIZE / ancho0)
    nuevo_ancho, nuevo_alto = int(round(ancho0 * escala)), int(round(alto0 * escala))
    redimensionada = cv2.resize(imagen_bgr, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_LINEAR)

    lienzo = np.full((YOLO_INPUT_SIZE, YOLO_INPUT_SIZE, 3), 114, dtype=np.uint8)
    relleno_x = (YOLO_INPUT_SIZE - nuevo_ancho) // 2
    relleno_y = (YOLO_INPUT_SIZE - nuevo_alto) // 2
    lienzo[relleno_y:relleno_y + nuevo_alto, relleno_x:relleno_x + nuevo_ancho] = redimensionada

    entrada = lienzo[:, :, ::-1].astype(np.float32) / 255.0  # BGR -> RGB, 0-1
    entrada = entrada.transpose(2, 0, 1)[None, ...]  # HWC -> NCHW
    return entrada, escala, relleno_x, relleno_y


def detectar_objetos_yolo(imagen_bgr):
    """Corre YOLOv8 sobre la foto y devuelve una lista de detecciones (caja,
    confianza y nombre de clase) en las coordenadas de la imagen original.
    Es información complementaria: no es lo que cuenta las matas."""
    sesion = _cargar_sesion_yolo()
    entrada, escala, relleno_x, relleno_y = _preprocesar_para_yolo(imagen_bgr)

    nombre_entrada = sesion.get_inputs()[0].name
    salida = sesion.run(None, {nombre_entrada: entrada})[0]
    salida = np.squeeze(salida).T  # (8400, 84) -> filas = candidatos

    cajas, puntajes, clases = [], [], []
    for fila in salida:
        puntajes_clase = fila[4:]
        clase_id = int(np.argmax(puntajes_clase))
        confianza = float(puntajes_clase[clase_id])
        if confianza < YOLO_CONF_THRESHOLD:
            continue
        cx, cy, w, h = fila[:4]
        cajas.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])
        puntajes.append(confianza)
        clases.append(clase_id)

    if not cajas:
        return []

    indices = cv2.dnn.NMSBoxes(
        [[c[0], c[1], c[2] - c[0], c[3] - c[1]] for c in cajas],
        puntajes, YOLO_CONF_THRESHOLD, YOLO_IOU_THRESHOLD,
    )
    if len(indices) == 0:
        return []

    alto0, ancho0 = imagen_bgr.shape[:2]
    detecciones = []
    for i in np.array(indices).flatten():
        x1, y1, x2, y2 = cajas[i]
        x1 = max(0, (x1 - relleno_x) / escala)
        y1 = max(0, (y1 - relleno_y) / escala)
        x2 = min(ancho0, (x2 - relleno_x) / escala)
        y2 = min(alto0, (y2 - relleno_y) / escala)
        nombre_clase = COCO_CLASSES[clases[i]] if clases[i] < len(COCO_CLASSES) else f'clase {clases[i]}'
        detecciones.append({
            'caja': (int(x1), int(y1), int(x2), int(y2)),
            'confianza': puntajes[i],
            'clase': nombre_clase,
        })
    return detecciones


def contar_matas_por_vegetacion(imagen_bgr):
    """Estima cuántas matas hay en la foto a partir de las manchas de
    vegetación (técnica de Índice de Verde Excesivo + componentes
    conectados). Devuelve (cantidad_estimada, máscara_binaria, contornos)."""
    b, g, r = cv2.split(imagen_bgr.astype(np.int32))
    exg = np.clip(2 * g - r - b, 0, 255).astype(np.uint8)

    _, mascara = cv2.threshold(exg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=2)

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_total = imagen_bgr.shape[0] * imagen_bgr.shape[1]
    area_minima = max(80, area_total * 0.00035)
    contornos_validos = [c for c in contornos if cv2.contourArea(c) >= area_minima]

    cantidad_estimada = 0
    if contornos_validos:
        areas = sorted(cv2.contourArea(c) for c in contornos_validos)
        area_tipica = areas[len(areas) // 2] or 1.0
        for c in contornos_validos:
            # Si una mancha es varias veces más grande que el tamaño típico
            # de una mata, es porque son varias matas juntas/traslapadas en
            # la foto: se cuentan como esa cantidad estimada en vez de 1.
            veces = max(1, round(cv2.contourArea(c) / area_tipica))
            cantidad_estimada += veces

    return cantidad_estimada, mascara, contornos_validos


def _redimensionar_si_es_muy_grande(imagen_bgr, lado_maximo=1600):
    alto, ancho = imagen_bgr.shape[:2]
    lado_mayor = max(alto, ancho)
    if lado_mayor <= lado_maximo:
        return imagen_bgr
    factor = lado_maximo / lado_mayor
    return cv2.resize(imagen_bgr, (int(ancho * factor), int(alto * factor)), interpolation=cv2.INTER_AREA)


def procesar_imagen(ruta_imagen, carpeta_salida):
    """Corre el análisis completo sobre una foto ya guardada en disco y
    deja una copia anotada (círculos verdes = matas contadas, cajas
    naranjas = detecciones de YOLO) en carpeta_salida. Devuelve un
    diccionario con los resultados para mostrar en la página."""
    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        raise ValueError(
            'No se pudo leer el archivo como imagen. Sube una foto en formato JPG o PNG.'
        )

    imagen = _redimensionar_si_es_muy_grande(imagen)

    cantidad_matas, _mascara, contornos = contar_matas_por_vegetacion(imagen)

    try:
        detecciones_yolo = detectar_objetos_yolo(imagen)
    except Exception:
        # Si el modelo YOLO falla por cualquier motivo, igual se entrega el
        # conteo de matas (que no depende de YOLO), en vez de tumbar toda
        # la herramienta.
        detecciones_yolo = []

    anotada = imagen.copy()
    for contorno in contornos:
        (x, y), radio = cv2.minEnclosingCircle(contorno)
        cv2.circle(anotada, (int(x), int(y)), max(8, int(radio)), (20, 255, 57), 2)

    for deteccion in detecciones_yolo:
        x1, y1, x2, y2 = deteccion['caja']
        cv2.rectangle(anotada, (x1, y1), (x2, y2), (0, 165, 255), 2)
        etiqueta = f"{deteccion['clase']} {deteccion['confianza'] * 100:.0f}%"
        cv2.putText(
            anotada, etiqueta, (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1, cv2.LINE_AA,
        )

    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_salida = f"analisis_{uuid.uuid4().hex}.jpg"
    ruta_salida = os.path.join(carpeta_salida, nombre_salida)
    cv2.imwrite(ruta_salida, anotada, [cv2.IMWRITE_JPEG_QUALITY, 90])

    return {
        'cantidad_matas': cantidad_matas,
        'manchas_detectadas': len(contornos),
        'objetos_yolo': detecciones_yolo,
        'nombre_imagen_resultado': nombre_salida,
    }
