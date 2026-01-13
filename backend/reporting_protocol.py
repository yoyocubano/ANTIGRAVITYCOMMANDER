# reporting_protocol.py
from datetime import datetime
import json
import requests
from typing import Dict, Optional

class AgentReporter:
    def __init__(self, agent_id: str, server_url: str = "http://localhost:8765/reports"):
        self.agent_id = agent_id
        self.server_url = server_url
        
    def start_task(self, task_id: str, description: str, estimated_duration: float = None):
        """Reporta inicio de tarea"""
        self._send_report({
            'event': 'TASK_START',
            'task_id': task_id,
            'task': {
                'id': task_id,
                'description': description,
                'estimated_duration': estimated_duration,
                'progress': 0
            },
            'timestamp': datetime.now().isoformat()
        })
        
    def update_progress(self, progress: int, status_message: str):
        """Actualiza progreso"""
        self._send_report({
            'event': 'TASK_PROGRESS',
            'progress': progress,
            'message': status_message,
            'timestamp': datetime.now().isoformat()
        })
        
    def complete_task(self, result: Dict = None):
        """Reporta tarea completada"""
        self._send_report({
            'event': 'TASK_COMPLETE',
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    def report_error(self, error_message: str):
        """Reporta error"""
        self._send_report({
            'event': 'TASK_ERROR',
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })
        
    def request_collaboration(self, target_agent: str, task_description: str):
        """Solicita colaboración"""
        self._send_report({
            'event': 'COLLABORATION_REQUEST',
            'target_agent': target_agent,
            'description': task_description,
            'timestamp': datetime.now().isoformat()
        })
        
    def request_more_tasks(self):
        """Solicita más trabajo (cuando está idle)"""
        self._send_report({
            'event': 'IDLE_REQUEST',
            'timestamp': datetime.now().isoformat()
        })
        
    def _send_report(self, data: Dict):
        """Envía el reporte al servidor vía HTTP POST"""
        data['agent_id'] = self.agent_id
        try:
            # Ahora sí enviamos los datos de verdad
            response = requests.post(self.server_url, json=data, timeout=1)
            # print(f"📡 Reporte enviado ({response.status_code})")
        except Exception as e:
            # Silencioso para no ensuciar logs si el dashboard no está activo
            pass
