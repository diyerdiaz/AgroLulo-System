# Imagen de Docker para AgroLulo System (Flask + SQLite)
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc y hace que los logs salgan sin
# buffer (para verlos en tiempo real con "docker compose logs -f").
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Las dependencias se instalan primero, en su propia capa: así Docker no
# tiene que reinstalarlas cada vez que solo cambia el código de la app.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Carpeta donde SQLite guarda la base de datos (flaskdb.sqlite). Se monta
# como volumen desde docker-compose.yml para que los datos NO se pierdan
# cada vez que se recrea el contenedor.
RUN mkdir -p instance

# La app no corre como root: si alguien lograra entrar por ella, no tendría
# permisos de administrador dentro del contenedor. Ver docker/entrypoint.sh.
RUN useradd --uid 1000 --no-create-home agrolulo \
    && mkdir -p app/static/uploads \
    && chown -R agrolulo instance app/static/uploads

EXPOSE 5000

# Un solo worker (--workers 1): config.py genera una SECRET_KEY nueva y
# distinta cada vez que arranca la app. Con más de un worker, cada
# proceso tendría su propia clave y las sesiones (inicio de sesión)
# fallarían de forma intermitente según qué worker atendiera cada
# petición. Con un solo worker se evita ese problema (si defines
# SECRET_KEY fija en tu .env, sí podrías subir --workers de forma segura).
#
# --threads: el worker atiende varias peticiones a la vez. Con uno solo,
# mientras se crea una contraseña toda la página queda esperando, y cada
# archivo CSS o JS hace fila detrás del anterior.
#
# --max-requests: reinicia el worker cada ~5000 peticiones (con
# --max-requests-jitter para que no coincida siempre en el mismo número).
# Es una red de seguridad: si algo va dejando memoria sin liberar poco a
# poco, esto evita que se acumule hasta tumbar el servidor. Cada página pide
# unos 12 archivos, así que un número bajo reiniciaría la app a cada rato.
ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "--max-requests", "5000", "--max-requests-jitter", "500", "run:app"]
