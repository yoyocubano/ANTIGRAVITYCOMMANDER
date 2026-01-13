# persistent_memory.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class PersistentMemory:
    def __init__(self, db_path="antigravity-memory.db"):
        self.db_path = db_path
        self._init_schema()
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_schema(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla de tareas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            task_id TEXT PRIMARY KEY,
            agent_id TEXT,
            task_type TEXT,
            description TEXT,
            status TEXT,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            result JSON,
            metadata JSON
        )
        ''')
        
        # Tabla de conocimiento (Knowledge Base)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            key TEXT PRIMARY KEY,
            value JSON,
            category TEXT,
            confidence REAL,
            source TEXT,
            updated_at TEXT
        )
        ''')
        
        # Tabla de conversaciones
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            metadata JSON
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def store_task(self, task_data: Dict):
        """Almacena o actualiza una tarea"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO task_history 
        (task_id, agent_id, task_type, description, status, start_time, end_time, duration, result, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data.get('task_id'),
            task_data.get('agent_id'),
            task_data.get('task_type'),
            task_data.get('description'),
            task_data.get('status'),
            str(task_data.get('start_time')),
            str(task_data.get('end_time')),
            task_data.get('duration'),
            json.dumps(task_data.get('result', {})),
            json.dumps(task_data.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
        
    def learn_from_history(self, task_type: str, limit: int = 10) -> List[Dict]:
        """Recupera tareas pasadas para aprender"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT description, result, duration 
        FROM task_history 
        WHERE task_type = ? AND status = 'completed'
        ORDER BY duration ASC 
        LIMIT ?
        ''', (task_type, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'description': row[0],
                'result': json.loads(row[1]) if row[1] else {},
                'duration': row[2]
            })
            
        conn.close()
        return results
        
    def store_knowledge(self, key: str, value: Any, category: str = 'general'):
        """Almacena conocimiento aprendido"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO knowledge_base 
        (key, value, category, confidence, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            key,
            json.dumps(value),
            category,
            1.0,
            'learning',
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
    def get_agent_performance(self, agent_id: str, days: int = 7) -> Dict:
        """Obtiene métricas de performance de un agente"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as successful,
            AVG(duration) as avg_dur
        FROM task_history 
        WHERE agent_id = ? AND start_time > ?
        ''', (agent_id, start_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
            
        total = row[0] or 0
        successful = row[1] or 0
        avg_dur = row[2] or 0
        
        return {
            'total_tasks': total,
            'success_rate': (successful / total) if total > 0 else 0,
            'avg_duration': avg_dur
        }
