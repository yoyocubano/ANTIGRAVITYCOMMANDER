#!/usr/bin/env python3
import sys
import os
import asyncio

# Añadir explícitamente la carpeta 'backend' al path de Python
# para que el agente pueda encontrar sus módulos hermanos.
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

print(f"🚀 Lanzando AntiGravity CLI desde: {backend_dir}")

# Importar la clase del agente desde el módulo en backend
try:
    from backend.init_cli import AntiGravityCLI
except ImportError:
    # Fallback si el path ya incluye backend implícitamente
    from init_cli import AntiGravityCLI

if __name__ == "__main__":
    cli = AntiGravityCLI(config_path=".antigravityrc")
    try:
        asyncio.run(cli.start())
    except KeyboardInterrupt:
        print("\n🛑 Agente detenido por el usuario.")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
