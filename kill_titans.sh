#!/bin/bash
# kill_titans.sh - Detiene los procesos de AntiGravity

echo "⛔ Deteniendo Protocolo TITAN..."

# Matar procesos escuchando en puertos 8765 y 8766
lsof -ti:8765 | xargs kill -9 2>/dev/null
lsof -ti:8766 | xargs kill -9 2>/dev/null

echo "✅ Puertos liberados (8765/8766)."
echo "💀 Procesos zombies eliminados."
