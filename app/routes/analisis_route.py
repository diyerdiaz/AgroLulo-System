import os

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.ml.conteo_matas import procesar_imagen

bp = Blueprint('analisis', __name__)

EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg'}


def _extension_valida(nombre_archivo):
    return '.' in nombre_archivo and nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS


@bp.route('/analisis', methods=['GET', 'POST'])
@login_required
def index():
    """Herramienta de Análisis: el usuario sube una foto de su cultivo y la
    aplicación cuenta cuántas matas (plantas) hay, apoyada en YOLO como
    detector de objetos y en una técnica de análisis de vegetación para el
    conteo (ver app/ml/conteo_matas.py para el detalle)."""
    resultado = None

    if request.method == 'POST':
        archivo = request.files.get('foto')

        if not archivo or archivo.filename == '':
            flash('Debes seleccionar una foto para analizar.', 'danger')
            return redirect(url_for('analisis.index'))

        if not _extension_valida(archivo.filename):
            flash('Formato no válido. Sube una imagen en JPG o PNG.', 'danger')
            return redirect(url_for('analisis.index'))

        carpeta_analisis = os.path.join(current_app.static_folder, 'uploads', 'analisis')
        os.makedirs(carpeta_analisis, exist_ok=True)

        nombre_seguro = secure_filename(archivo.filename) or 'foto.jpg'
        ruta_temporal = os.path.join(carpeta_analisis, f"tmp_{current_user.idUser}_{nombre_seguro}")
        archivo.save(ruta_temporal)

        try:
            resultado = procesar_imagen(ruta_temporal, carpeta_analisis)
        except Exception as e:
            flash(f'No se pudo analizar la imagen: {e}', 'danger')
            return redirect(url_for('analisis.index'))
        finally:
            # Solo se conserva la imagen ya anotada con el resultado; la
            # foto original subida no hace falta guardarla aparte.
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)

    return render_template('analisis/index.html', resultado=resultado)
