import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
import os

# Configure logging to be less verbose
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Standard template folder inside backend
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24)

# Configuración robusta para Render:
# 1. CORS permisivo (permitir conexiones desde el propio dominio y externos)
# 2. PermitirPolling (necesario para atravesar proxies de Render)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    ping_timeout=60, 
    ping_interval=25,
    always_connect=True
)

class DashboardManager:
    def __init__(self):
        self.agents = {}
        self.task_queue = []
        self.completed_tasks = []
        self.active_collaborations = []
        self.active_tasks = {}
        
    def update_agent_status(self, agent_id, status):
        self.agents[agent_id] = {
            **self.agents.get(agent_id, {}),
            **status,
            'last_update': datetime.now().isoformat()
        }
        socketio.emit('agent_update', {
            'agent_id': agent_id,
            'status': self.agents[agent_id]
        })
    
    def add_task(self, task):
        if 'id' not in task:
            task['id'] = f"task_{len(self.completed_tasks) + len(self.task_queue)}"
        task['timestamp'] = datetime.now().isoformat()
        self.task_queue.append(task)
        socketio.emit('new_task', task)
        return task
    
    def start_task(self, task_id, agent_id):
        to_remove = None
        for t in self.task_queue:
            if t['id'] == task_id:
                to_remove = t
                break
        if to_remove:
            self.task_queue.remove(to_remove)
            self.active_tasks[task_id] = to_remove
            self.active_tasks[task_id]['agent_id'] = agent_id
            self.active_tasks[task_id]['start_time'] = datetime.now()
    
    def complete_task(self, task_id, result):
        task = self.active_tasks.get(task_id)
        if not task:
            task = next((t for t in self.task_queue if t['id'] == task_id), None)
            if task: self.task_queue.remove(task)
        else:
            del self.active_tasks[task_id]
            
        if task:
            task['completed_at'] = datetime.now().isoformat()
            task['result'] = result
            if 'start_time' in task and isinstance(task['start_time'], datetime):
                task['duration'] = (datetime.now() - task['start_time']).total_seconds()
            self.completed_tasks.append(task)
            socketio.emit('task_complete', task)
    
    def report_collaboration(self, from_agent, to_agent, task):
        collab = {
            'from': from_agent,
            'to': to_agent,
            'task': task,
            'timestamp': datetime.now().isoformat()
        }
        self.active_collaborations.append(collab)
        socketio.emit('collaboration', collab)
    
    def get_system_metrics(self):
        return {
            'total_agents': len(self.agents),
            'active_agents': len([a for a in self.agents.values() if a.get('status') == 'busy']),
            'tasks_in_queue': len(self.task_queue),
            'tasks_completed': len(self.completed_tasks),
            'active_collaborations': len(self.active_collaborations),
            'avg_task_duration': self._calculate_avg_duration()
        }
    
    def _calculate_avg_duration(self):
        if not self.completed_tasks: return 0
        durations = [t.get('duration', 0) for t in self.completed_tasks if 'duration' in t]
        if not durations: return 0
        return sum(durations) / len(durations)

    def process_report(self, data):
        """Procesa datos unificados (Socket o HTTP)"""
        agent_id = data.get('agent_id', 'unknown')
        event_type = data.get('event')
        
        if event_type == 'TASK_START':
            task_id = data['task_id']
            self.start_task(task_id, agent_id)
            self.update_agent_status(agent_id, {'status': 'busy', 'current_task': data['task']})
        elif event_type == 'TASK_PROGRESS':
            current = self.agents.get(agent_id, {})
            if 'current_task' in current and current['current_task']:
                current['current_task']['progress'] = data['progress']
                self.update_agent_status(agent_id, current)
        elif event_type == 'TASK_COMPLETE':
            task_info = data.get('result', {}) # Or manage task_id
            # Simplified completion logic for visualization
            self.update_agent_status(agent_id, {'status': 'idle', 'current_task': None})
            # Also emit general task complete if task ID matches active
            # For simplicity we just ensure UI updates agent status
            socketio.emit('task_complete', {'agent_id': agent_id, 'description': 'Tarea completada'})
            
        elif event_type == 'COLLABORATION_REQUEST':
            self.report_collaboration(agent_id, data['target_agent'], data['description'])
        elif event_type == 'IDLE_REQUEST':
            self.update_agent_status(agent_id, {'status': 'idle', 'requesting_work': True})
            socketio.emit('work_available', {'agent_id': agent_id})


dashboard = DashboardManager()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/health')
def health():
    return json.dumps({'status': 'healthy', 'agents': len(dashboard.agents)})

# --- NEW: HTTP REST Endpoint for Reporting ---
@app.route('/reports', methods=['POST'])
def receive_report():
    data = request.json
    dashboard.process_report(data)
    return jsonify({'status': 'received'})

@app.route('/favicon.ico')
def favicon():
    return "", 204

@socketio.on('connect')
def handle_connect():
    emit('initial_state', {
        'agents': dashboard.agents,
        'task_queue': dashboard.task_queue,
        'completed_tasks': dashboard.completed_tasks[-50:],
        'metrics': dashboard.get_system_metrics()
    })

@socketio.on('agent_report')
def handle_socket_report(data):
    dashboard.process_report(data)

@socketio.on('request_metrics')
def handle_metrics_request():
    emit('metrics_update', dashboard.get_system_metrics())

if __name__ == '__main__':
    print("🚀 Dashboard Server running at http://0.0.0.0:8765")
    try:
        socketio.run(app, host='0.0.0.0', port=8765, debug=False, allow_unsafe_werkzeug=True)
    except OSError:
        print("❌ Port 8765 is busy. Please run ./kill_titans.sh")
