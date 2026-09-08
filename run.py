import os
from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # El modo debug queda APAGADO por defecto: dejarlo prendido en un
    # servidor real es un riesgo de seguridad (muestra el código fuente y
    # una consola interactiva si algo falla). Si necesitas depurar en tu
    # propia máquina, actívalo solo ahí escribiendo antes de correr esto:
    #   Windows (PowerShell):  $env:FLASK_DEBUG="1"
    #   Windows (cmd):         set FLASK_DEBUG=1
    #   Linux / Mac:           export FLASK_DEBUG=1
    modo_debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=modo_debug, host='0.0.0.0', port=5000)