#!/usr/bin/env python3
# init_cli.py
import os
import sys
import asyncio
import argparse
from pathlib import Path
import json
import random
import websockets
from dotenv import load_dotenv

# Ensure we can import from the backend directory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from intelligent_cache import IntelligentCache
from persistent_memory import PersistentMemory
from reporting_protocol import AgentReporter
from sync_manager import SyncManager, DistributedCache
from telemetry import TelemetrySystem, StructuredLogger

class AntiGravityCLI:
    def __init__(self, config_path=".antigravityrc"):
        self.config = self._load_config()
        self.agent_id = self.config['AGENT_ID']
        
        # We postpone initialization of Async objects (like SyncManager's potential queue)
        # to the start() method where the loop is running.
        self.telemetry = None
        self.logger = None
        self.cache = None
        self.memory = None
        self.reporter = None
        self.sync_manager = None
        self.distributed_cache = None
        
        self.status = 'initializing'
        self.task_queue = None # Will init in start
        self.ws_connection = None
        self.reconnect_delay = 5

    def _load_config(self):
        config = {}
        config_path = Path(".antigravityrc")
        if config_path.exists():
            with open(config_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        config[k] = v.strip('"\'')
        defaults = {
            'AGENT_ID': f'cli-primary-{random.randint(1000,9999)}',
            'AGENT_TYPE': 'command-line',
            'AGENT_CAPABILITIES': 'code_generation,file_operations,api_calls,data_processing,shell_commands,git_operations,general',
            'MAX_CONCURRENT_TASKS': '5',
            'CACHE_DIR': '.antigravity-cache',
            'CACHE_MAX_SIZE_MB': '500',
            'MEMORY_DB_PATH': 'antigravity-memory.db',
            'REPORT_ENDPOINT': 'https://antigravitycommander.onrender.com/reports',
            'COORDINATION_SERVER': 'wss://antigravitycommander.onrender.com',
            'ENABLE_REALTIME_REPORTING': 'true',
            'AUTO_REQUEST_TASKS': 'true',
            'HEARTBEAT_INTERVAL_MS': '5000',
            'IDLE_TIMEOUT_SECONDS': '10'
        }
        for k, v in defaults.items():
            if k not in config: config[k] = v
        return config

    async def _init_components(self):
        """Asynchronous component initialization"""
        self.telemetry = TelemetrySystem()
        self.logger = StructuredLogger(self.agent_id, self.telemetry)
        
        cache_path = self.config.get('CACHE_DIR', '.antigravity-cache')
        self.cache = IntelligentCache(
            cache_dir=cache_path,
            max_size_mb=int(self.config['CACHE_MAX_SIZE_MB'])
        )
        self.memory = PersistentMemory(self.config['MEMORY_DB_PATH'])
        self.reporter = AgentReporter(self.agent_id, self.config['REPORT_ENDPOINT'])
        
        self.sync_manager = SyncManager()
        self.distributed_cache = DistributedCache(self.sync_manager)
        
        self.task_queue = asyncio.Queue()
        
        self.logger.info("AntiGravity CLI Initialized (Async Loop Active)", config=self.config)

    async def start(self):
        # Init components inside the running loop
        await self._init_components()
        self.logger.info("🚀 Iniciando AntiGravity CLI Agent")
        await self._connection_manager()

    async def _connection_manager(self):
        while True:
            try:
                await self._connect_to_coordination_server()
                await self._register_agent()
                self.reconnect_delay = 5
                
                tasks = [
                    asyncio.create_task(self._task_processor()),
                    asyncio.create_task(self._heartbeat_worker()),
                    asyncio.create_task(self._auto_request_worker()),
                    asyncio.create_task(self.sync_manager.start_sync_worker()),
                    asyncio.create_task(self._message_receiver())
                ]
                
                self.status = 'idle'
                if self.config['AUTO_REQUEST_TASKS'] == 'true':
                    await self._request_task_from_coordinator()

                await asyncio.gather(*tasks)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ Desconectado: {e}")
                else:
                    print(f"❌ Error crítico: {e}")
                self.ws_connection = None
                
            print(f"🔄 Reintentando en {self.reconnect_delay}s...")
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, 60)

    async def _connect_to_coordination_server(self):
        uri = self.config['COORDINATION_SERVER']
        # self.logger.info(f"Conectando a {uri}...") # Reduce noise
        self.ws_connection = await websockets.connect(uri)
        self.logger.info("✅ Conectado al servidor")

    async def _register_agent(self):
        caps = self.config['AGENT_CAPABILITIES'].split(',')
        reg_data = {
            'type': 'AGENT_REGISTER',
            'agent': {
                'agent_id': self.agent_id,
                'type': self.config['AGENT_TYPE'],
                'capabilities': caps,
                'max_concurrent_tasks': int(self.config['MAX_CONCURRENT_TASKS']),
                'status': 'idle'
            }
        }
        if self.ws_connection:
            await self.ws_connection.send(json.dumps(reg_data))

    async def _request_task_from_coordinator(self):
        if self.ws_connection:
            try:
                await self.ws_connection.send(json.dumps({
                    'type': 'TASK_REQUEST',
                    'agent_id': self.agent_id
                }))
            except: pass

    async def _message_receiver(self):
        if not self.ws_connection: return
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                if data.get('type') == 'TASK_ASSIGNMENT':
                    task = data.get('task')
                    await self.task_queue.put(task)
                    self.logger.info(f"📥 Tarea recibida: {task.get('id')}")
        except websockets.exceptions.ConnectionClosed:
            raise Exception("Connection closed")

    async def _task_processor(self):
        while True:
            if not self.ws_connection or self.ws_connection.closed:
                await asyncio.sleep(1)
                continue
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                try:
                    await self._execute_task(task)
                except Exception as e:
                    self.logger.error(f"Error tarea: {e}")
                    self.reporter.report_error(str(e))
                finally:
                    self.task_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception:
                await asyncio.sleep(1)

    async def _execute_task(self, task):
        self.status = 'busy'
        self.current_task = task
        self.reporter.start_task(task['id'], task['description'])
        
        start_time = asyncio.get_event_loop().time()
        cache_key = f"task:{task['type']}:{hash(str(task.get('description')))}"
        
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.info("✅ Obtenido de caché")
            result = cached
        else:
            self.logger.info(f"Ejecutando: {task['description']}")
            result = await self._route_and_execute(task)
            self.cache.set(cache_key, result, context=task)
            
        dur = asyncio.get_event_loop().time() - start_time
        
        if self.ws_connection:
            await self.ws_connection.send(json.dumps({
                'type': 'TASK_COMPLETE',
                'agent_id': self.agent_id,
                'task': task,
                'result': result
            }))
            
        self.reporter.complete_task(result=result)
        self.memory.store_task({
            'task_id': task['id'],
            'agent_id': self.agent_id,
            'task_type': task['type'],
            'description': task['description'],
            'status': 'completed',
            'start_time': start_time,
            'end_time': asyncio.get_event_loop().time(),
            'duration': dur,
            'result': result
        })
        self.telemetry.record_metric(f"task.{task['type']}.duration", dur)
        self.telemetry.record_metric(f"task.{task['type']}.success", 1)
        
        self.current_task = None
        self.status = 'idle'
        if self.config['AUTO_REQUEST_TASKS'] == 'true':
            await self._request_task_from_coordinator()

    async def _route_and_execute(self, task):
        t_type = task['type']
        if t_type == 'shell_commands':
            cmd = task.get('command')
            if cmd:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                return {'stdout': stdout.decode(), 'stderr': stderr.decode(), 'code': proc.returncode}
        
        await asyncio.sleep(1)
        return {'status': 'completed', 'note': f"Executed {t_type}"}

    async def _heartbeat_worker(self):
        interval = int(self.config['HEARTBEAT_INTERVAL_MS']) / 1000
        while True:
            await asyncio.sleep(interval)
            if self.ws_connection:
                try:
                    await self.ws_connection.send(json.dumps({
                        'type': 'HEARTBEAT',
                        'agent_id': self.agent_id,
                        'status': self.status
                    }))
                except: pass

    async def _auto_request_worker(self):
        if self.config['AUTO_REQUEST_TASKS'] != 'true': return
        timeout = int(self.config['IDLE_TIMEOUT_SECONDS'])
        while True:
            await asyncio.sleep(timeout)
            if self.status == 'idle' and self.task_queue.empty() and self.ws_connection:
                await self._request_task_from_coordinator()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='.antigravityrc')
    args = parser.parse_args()
    cli = AntiGravityCLI(config_path=args.config)
    try:
        asyncio.run(cli.start())
    except KeyboardInterrupt:
        print("Bye.")
        sys.exit(0)

if __name__ == '__main__':
    main()
