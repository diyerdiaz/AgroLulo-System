import os
import secrets

# Carga las variables del archivo .env (SECRET_KEY, MAIL_*, ...) también
# cuando se corre con "python run.py" o "flask run" fuera de Docker.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

    # Correo desde el que se envían los códigos de recuperación de
    # contraseña. Los datos reales van en el archivo .env (nunca en el
    # código). Con Gmail: activar la verificación en dos pasos en la cuenta
    # y crear una "contraseña de aplicación" para MAIL_PASSWORD.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_SENDER = os.environ.get('MAIL_SENDER') or os.environ.get('MAIL_USERNAME', '')

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt