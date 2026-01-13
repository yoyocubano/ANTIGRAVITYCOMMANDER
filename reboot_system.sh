#!/bin/bash
# reboot_system.sh - Protocolo de Reinicio Total y Limpieza

echo "🛑 DETENIENDO SISTEMA TITAN..."
./kill_titans.sh

echo "🧹 Limpiando archivos temporales y cachés corruptas..."
rm -rf .antigravity-cache/
mkdir .antigravity-cache

echo "🚀 INICIANDO PROTOCOLO DE ARRANQUE SECUENCIAL..."

# Iniciar Dashboard en background
echo "   -> Arrancando Dashboard Server (Puerto 8765)..."
source venv/bin/activate
nohup python dashboard_server.py > logs/dashboard.log 2>&1 &
DASH_PID=$!
echo "      [OK] Dashboard PID: $DASH_PID"

sleep 2

# Iniciar Coordinador en background
echo "   -> Arrancando Coordinador Maestro (Puerto 8766)..."
nohup python master_coordinator.py > logs/coordinator.log 2>&1 &
COORD_PID=$!
echo "      [OK] Coordinador PID: $COORD_PID"

sleep 2

# Iniciar Agente en background
echo "   -> Arrancando Agente Titan CLI..."
nohup python init_cli.py > logs/agent.log 2>&1 &
AGENT_PID=$!
echo "      [OK] Agente PID: $AGENT_PID"

echo "✅ SISTEMA REINICIADO AL 100%"
echo "---------------------------------------------------"
echo "📊 Dashboard: http://localhost:8765"
echo "📝 Logs disponibles en carpeta 'logs/'"
echo "---------------------------------------------------"
echo "Para detener todo, ejecuta: ./kill_titans.sh"
