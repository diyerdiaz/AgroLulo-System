#!/bin/bash

# 1. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
else
    echo "El entorno virtual ya existe."
fi

# 2. Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# 3. Actualizar pip
echo "Actualizando pip..."
pip install --upgrade pip

# 4. Instalar Flask (por si no está en requirements)
echo "Instalando Flask..."
pip install flask

# 5. Instalar dependencias si existe requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Instalando dependencias..."
    pip install -r requirements.txt
else
    echo "No se encontró requirements.txt"
fi

# 6. Ejecutar proyecto
echo "Ejecutando proyecto..."
python run.py

