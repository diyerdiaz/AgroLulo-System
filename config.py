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
    # Límite para los formularios de texto (notas, nombres...). Sin esto,
    # alguien podría llenar la base de datos con textos enormes. No afecta la
    # subida de fotos, que usa MAX_CONTENT_LENGTH.
    MAX_FORMULARIO_TEXTO = 16 * 1024

    # El token CSRF dura lo mismo que la sesión. Con el límite por defecto
    # (1 hora), un formulario abierto un buen rato fallaría al enviarse.
    WTF_CSRF_TIME_LIMIT = None

    # Poner DETRAS_DE_HTTPS=1 solo cuando la página esté publicada detrás de
    # un proxy con HTTPS (Caddy, Nginx...). Activa la cookie Secure y HSTS, y
    # hace que la IP se lea de ese proxy. Sin HTTPS debe quedar en 0: con la
    # cookie Secure, el navegador no guardaría la sesión y nadie podría entrar.
    DETRAS_DE_HTTPS = os.environ.get('DETRAS_DE_HTTPS', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = DETRAS_DE_HTTPS

    # Correo desde el que se envían los códigos de recuperación de
    # contraseña. Los datos reales van en el archivo .env (nunca en el
    # código). Con Gmail: activar la verificación en dos pasos en la cuenta
    # y crear una "contraseña de aplicación" para MAIL_PASSWORD.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_SENDER = os.environ.get('MAIL_SENDER') or os.environ.get('MAIL_USERNAME', '')
    # Dirección pública de la página. Se usa en los botones de los correos
    # (por ejemplo "Ya lo hice" en los recordatorios del calendario), que se
    # abren desde el celular de la persona y no saben dónde vive la página.
    APP_URL = os.environ.get('APP_URL', 'http://127.0.0.1:5001')

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt