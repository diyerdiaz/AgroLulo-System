import os
import secrets

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///flaskdb.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Si existe la variable de entorno SECRET_KEY (por ejemplo, la que trae
    # el archivo .env cuando se corre con "docker compose up") se usa esa,
    # para que el inicio de sesión no se pierda cada vez que se reinicia el
    # contenedor. Si no existe (por ejemplo, corriendo con "python run.py"
    # directamente como siempre se ha hecho), se sigue generando una nueva
    # al azar en cada arranque, igual que antes.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(24)

    # Límite de tamaño para cualquier petición/archivo subido (en bytes).
    # Sin esto, alguien podía mandar una foto gigante a "Análisis" (conteo
    # de matas con YOLO) y hacer que el servidor cargue toda esa imagen en
    # memoria antes de poder redimensionarla, lo que en un servidor con
    # poca RAM puede tumbar el proceso (visto en los logs como "WORKER
    # TIMEOUT" / "Perhaps out of memory?"). 10 MB es de sobra para una
    # foto de celular en JPG/PNG.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt