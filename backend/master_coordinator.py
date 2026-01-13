# master_coordinator.py (Optimized)
import asyncio
import json
from datetime import datetime
from typing import Dict, List
import websockets
import sys
import os
import signal

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from task_router import IntelligentTaskRouter
from sync_manager import SyncManager
from telemetry import TelemetrySystem

class MasterCoordinator:
    def __init__(self):
        self.agents = {}
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.completed_tasks = []
        self.router = IntelligentTaskRouter()
        self.sync_manager = SyncManager()
        self.telemetry = TelemetrySystem()
        self.server = None
        
    async def start_server(self, host='0.0.0.0', port=8766):
        """Inicia servidor de coordinación"""
        try:
            self.server = await websockets.serve(self.handle_connection, host, port)
            print(f"🚀 Coordinador maestro iniciado en ws://{host}:{port}")
            await asyncio.Future()  # Run forever
        except OSError as e:
            if e.errno == 48:
                print(f"❌ Error: El puerto {port} ya está en uso.")
                print("💡 Ejecuta './kill_titans.sh' para liberar los puertos.")
                sys.exit(1)
            else:
                raise e
    
    async def handle_connection(self, websocket, path):
        """Maneja conexión de agente"""
        agent_id = None
        
        try:
            async for message in websocket:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'AGENT_REGISTER':
                    agent_id = await self.register_agent(data['agent'], websocket)
                    
                elif message_type == 'HEARTBEAT':
                    await self.handle_heartbeat(data)
                    
                elif message_type == 'TASK_REQUEST':
                    await self.assign_task_to_agent(agent_id)
                    
                elif message_type == 'TASK_COMPLETE':
                    await self.handle_task_completion(data)
                    
                elif message_type == 'TASK_DELEGATION':
                    await self.handle_delegation(data)
                    
                elif message_type == 'CONTEXT_SYNC':
                    if agent_id:
                        await self.sync_manager.update_context(
                            agent_id,
                            'agent_context',
                            data['context']
                        )
                    
        except websockets.exceptions.ConnectionClosed:
            if agent_id:
                # print(f"❌ Agente {agent_id} desconectado") # Logging menos ruidoso
                if agent_id in self.agents:
                    self.agents[agent_id]['status'] = 'disconnected'
                    await self.broadcast_system_status()
    
    async def register_agent(self, agent_data, websocket):
        """Registra nuevo agente"""
        agent_id = agent_data['agent_id']
        
        self.agents[agent_id] = {
            **agent_data,
            'websocket': websocket,
            'status': 'idle',
            'registered_at': datetime.now()
        }
        
        # Registrar en router
        self.router.register_agent(
            agent_id,
            agent_data['capabilities']
        )
        
        print(f"✅ Agente registrado: {agent_id}")
        
        # Broadcast actualización
        await self.broadcast_system_status()
        
        return agent_id
    
    async def assign_task_to_agent(self, requesting_agent_id=None):
        """Asigna tarea a agente"""
        if self.task_queue.empty():
            return
        
        task = await self.task_queue.get()
        
        # Rutear al mejor agente
        try:
            best_agent_id = None
            if requesting_agent_id and self._can_handle_task(requesting_agent_id, task):
                best_agent_id = requesting_agent_id
            else:
                try:
                    best_agent_id = self.router.route_task(task)
                except:
                    if requesting_agent_id:
                        best_agent_id = requesting_agent_id
            
            if not best_agent_id or best_agent_id not in self.agents:
                # Reencolar si no hay agente
                await self.task_queue.put(task)
                return

            agent = self.agents[best_agent_id]
            
            # Enviar tarea
            await agent['websocket'].send(json.dumps({
                'type': 'TASK_ASSIGNMENT',
                'task': task
            }))
            
            self.active_tasks[task['id']] = {
                'task': task,
                'agent': best_agent_id,
                'started_at': datetime.now()
            }
            
            print(f"📤 Tarea {task['id']} asignada a {best_agent_id}")
            
        except Exception as e:
            print(f"❌ Error asignando tarea: {e}")
            await self.task_queue.put(task)
    
    def _can_handle_task(self, agent_id, task):
        """Verifica si agente puede manejar tarea"""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        return 'general' in agent.get('capabilities', []) or task['type'] in agent.get('capabilities', [])
    
    async def handle_task_completion(self, data):
        """Maneja completación de tarea"""
        task_info = data.get('task', {})
        task_id = task_info.get('id')
        agent_id = data.get('agent_id')
        
        if task_id in self.active_tasks:
            active_info = self.active_tasks[task_id]
            duration = (datetime.now() - active_info['started_at']).total_seconds()
            
            self.router.report_task_completion(
                agent_id,
                active_info['task'],
                success=True,
                duration=duration
            )
            
            self.completed_tasks.append({
                **active_info,
                'completed_at': datetime.now(),
                'duration': duration,
                'result': data.get('result')
            })
            
            del self.active_tasks[task_id]
            
            print(f"✅ Tarea {task_id} completada por {agent_id} en {duration:.2f}s")
            
            if agent_id in self.agents:
                self.agents[agent_id]['status'] = 'idle'
            
            await self.broadcast_system_status()
    
    async def handle_delegation(self, data):
        """Maneja delegación entre agentes"""
        from_agent = data.get('from')
        to_agent = data.get('to')
        task = data.get('task')
        
        print(f"🤝 Delegación: {from_agent} → {to_agent}")
        
        new_task = {
            'id': f"task_{len(self.completed_tasks) + len(self.active_tasks)}_del",
            'type': task.get('type', 'general'),
            'description': task.get('description', str(task)),
            'delegated_from': from_agent,
            'priority': 'normal'
        }
        
        await self.task_queue.put(new_task)
        
        if to_agent in self.agents and self.agents[to_agent]['status'] == 'idle':
            await self.assign_task_to_agent(to_agent)
    
    async def handle_heartbeat(self, data):
        """Maneja heartbeat de agente"""
        agent_id = data.get('agent_id')
        
        if agent_id in self.agents:
            self.agents[agent_id]['last_heartbeat'] = datetime.now()
            self.agents[agent_id]['status'] = data.get('status', 'idle')
    
    async def broadcast_system_status(self):
        """Broadcast estado del sistema a todos los agentes"""
        status = {
            'type': 'SYSTEM_STATUS_UPDATE',
            'status': {
                'total_agents': len(self.agents),
                'active_agents': len([a for a in self.agents.values() if a['status'] == 'busy']),
                'idle_agents': len([a for a in self.agents.values() if a['status'] == 'idle']),
                'tasks_in_queue': self.task_queue.qsize(),
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks)
            }
        }
        
        for agent in self.agents.values():
            if 'websocket' in agent:
                try:
                    await agent['websocket'].send(json.dumps(status))
                except:
                    pass
    
    async def monitor_agents(self):
        """Monitorea salud de agentes"""
        while True:
            await asyncio.sleep(30)
            
            current_time = datetime.now()
            for agent_id, agent in self.agents.items():
                if 'last_heartbeat' in agent and isinstance(agent['last_heartbeat'], datetime):
                    time_since_heartbeat = (current_time - agent['last_heartbeat']).total_seconds()
                    
                    if time_since_heartbeat > 60:
                        agent['status'] = 'unresponsive'


# Script de inicio
async def main():
    coordinator = MasterCoordinator()
    
    # Iniciar servidor
    server_task = asyncio.create_task(
        coordinator.start_server('0.0.0.0', 8766)
    )
    
    # Iniciar monitor
    monitor_task = asyncio.create_task(
        coordinator.monitor_agents()
    )
    
    await asyncio.gather(server_task, monitor_task)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Cerrando Coordinador Maestro")
