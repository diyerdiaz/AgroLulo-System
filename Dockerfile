# Imagen de Docker para AgroLulo System (Flask + SQLite)
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc y hace que los logs salgan sin
# buffer (para verlos en tiempo real con "docker compose logs -f").
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libzbar0: librería del sistema que necesita "pyzbar" para leer los
# códigos QR (la usa la función de leer QR de usuarios, en
# app/routes/users_route.py). Sin esto esa función puntual fallaría.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Las dependencias se instalan primero, en su propia capa: así Docker no
# tiene que reinstalarlas cada vez que solo cambia el código de la app.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn pyzbar

COPY . .

# Carpeta donde SQLite guarda la base de datos (flaskdb.sqlite). Se monta
# como volumen desde docker-compose.yml para que los datos NO se pierdan
# cada vez que se recrea el contenedor.
RUN mkdir -p instance

EXPOSE 5000

# Un solo worker (--workers 1): config.py genera una SECRET_KEY nueva y
# distinta cada vez que arranca la app. Con más de un worker, cada
# proceso tendría su propia clave y las sesiones (inicio de sesión)
# fallarían de forma intermitente según qué worker atendiera cada
# petición. Con un solo worker se evita ese problema.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "run:app"]
