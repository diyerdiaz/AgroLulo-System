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

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt