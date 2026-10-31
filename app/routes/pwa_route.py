from flask import Blueprint, current_app, render_template, send_from_directory

bp = Blueprint('pwa', __name__)


@bp.route('/sw.js')
def service_worker():
    """El archivo vive en static/js, pero se sirve desde la raíz: un service
    worker solo controla las direcciones que están por debajo de la suya."""
    respuesta = send_from_directory(current_app.static_folder, 'js/sw.js', mimetype='text/javascript')
    respuesta.headers['Cache-Control'] = 'no-cache'
    return respuesta


@bp.route('/offline')
def offline():
    """Pantalla que se muestra en la app instalada cuando no hay internet."""
    return render_template('pwa/offline.html')
