#!/bin/bash

# AntiGravity Titans System - Setup Script
# "Funcionar al 500%"

echo "🚀 Iniciando Protocolo de Instalación TITAN..."

# Definir directorios
BASE_DIR="$(pwd)/.agent/titans_system"
CACHE_DIR="$(pwd)/.antigravity-cache"
OUTPUT_LOGS="$(pwd)/logs"

mkdir -p "$BASE_DIR/templates"
mkdir -p "$CACHE_DIR"
mkdir -p "$OUTPUT_LOGS"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instalando..."
    brew install python3
fi

# Crear entorno virtual si no existe
if [ ! -d "$BASE_DIR/venv" ]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv "$BASE_DIR/venv"
fi

# Activar entorno e instalar dependencias
source "$BASE_DIR/venv/bin/activate"
echo "📦 Instalando dependencias de alto rendimiento..."
pip install -r "$BASE_DIR/requirements.txt"

echo "✅ Entorno preparado."
echo "📂 Directorio del sistema: $BASE_DIR"
echo "🧠 Directorio de caché: $CACHE_DIR"

# Permisos de ejecución
chmod +x "$BASE_DIR"/*.py 2>/dev/null

echo "🔥 SISTEMA TITAN LISTO PARA INICIACIÓN."
