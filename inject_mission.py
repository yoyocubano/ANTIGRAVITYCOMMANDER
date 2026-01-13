# inject_mission.py
import asyncio
import websockets
import json

async def send_mission():
    uri = "ws://localhost:8766"
    
    mission = {
        "type": "TASK_DELEGATION",
        "from": "USER_COMMAND_CENTER",
        "to": "titan-cli-01",
        "task": {
            "id": f"mission_alpha_{json.dumps(str(asyncio.get_event_loop().time()))[-4:]}",
            "type": "shell_commands",
            "description": "Ejecutar diagnóstico de sistema y verificar conectividad",
            "command": "echo '🚀 TITAN SYSTEM DIAGNOSTIC' && date && echo '✅ CPU: OK' && echo '✅ RAM: OK' && echo '✅ NETWORK: SECURE'",
            "estimated_duration": 2.5
        }
    }
    
    print(f"📡 Conectando a {uri}...")
    async with websockets.connect(uri) as websocket:
        print("📤 Enviando Misión Alpha...")
        await websocket.send(json.dumps(mission))
        print("✅ Misión enviada con éxito.")

if __name__ == "__main__":
    asyncio.run(send_mission())
