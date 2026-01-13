# task_router.py
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime, timedelta

class IntelligentTaskRouter:
    def __init__(self):
        self.agents = {}
        self.task_history = []
        self.routing_stats = {}
        
    def register_agent(self, agent_id: str, capabilities: List[str], 
                       performance_profile: Optional[Dict] = None):
        """Registra un agente con sus capacidades"""
        self.agents[agent_id] = {
            'id': agent_id,
            'capabilities': set(capabilities),
            'status': 'idle',
            'current_load': 0,
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'avg_duration': 0,
            'specializations': {},
            'performance_profile': performance_profile or {}
        }
        
    def route_task(self, task: Dict) -> str:
        """Rutea una tarea al mejor agente disponible"""
        eligible_agents = self._find_eligible_agents(task)
        
        if not eligible_agents:
            raise Exception(f"No hay agentes disponibles para: {task['type']}")
        
        # Calcular scores para cada agente
        scored_agents = []
        for agent_id in eligible_agents:
            score = self._calculate_agent_score(agent_id, task)
            scored_agents.append((agent_id, score))
        
        # Ordenar por score descendente
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        best_agent = scored_agents[0][0]
        
        # Actualizar estado del agente
        self.agents[best_agent]['status'] = 'busy'
        self.agents[best_agent]['current_load'] += 1
        
        # Registrar decisión de routing
        self._log_routing_decision(task, best_agent, scored_agents)
        
        return best_agent
    
    def _find_eligible_agents(self, task: Dict) -> List[str]:
        """Encuentra agentes elegibles para una tarea"""
        required_capability = task.get('type', 'general')
        
        eligible = []
        for agent_id, agent in self.agents.items():
            # Debe estar idle o con baja carga
            if agent['status'] == 'idle' or agent['current_load'] < 3:
                # Debe tener la capacidad requerida
                if required_capability in agent['capabilities'] or 'general' in agent['capabilities']:
                    eligible.append(agent_id)
        
        return eligible
    
    def _calculate_agent_score(self, agent_id: str, task: Dict) -> float:
        """Calcula score de idoneidad de un agente para una tarea"""
        agent = self.agents[agent_id]
        score = 100.0
        
        # 1. Especialización (peso: 40%)
        task_type = task.get('type', 'general')
        if task_type in agent['specializations']:
            specialization_score = agent['specializations'][task_type]['success_rate']
            score += specialization_score * 40
        elif task_type in agent['capabilities']:
            score += 20  # Tiene capacidad pero no historial
        
        # 2. Carga actual (peso: 30%)
        load_penalty = agent['current_load'] * 15
        score -= load_penalty
        
        # 3. Tasa de éxito histórica (peso: 20%)
        if agent['total_tasks'] > 0:
            success_rate = agent['successful_tasks'] / agent['total_tasks']
            score += success_rate * 20
        
        # 4. Velocidad promedio (peso: 10%)
        if agent['avg_duration'] > 0 and task.get('priority') == 'high':
            # Para tareas prioritarias, favorecer agentes rápidos
            speed_score = 1 / (agent['avg_duration'] + 1)  # Evitar división por 0
            score += speed_score * 10
        
        # 5. Contexto similar (bonus)
        if self._has_similar_context(agent_id, task):
            score += 15
        
        # 6. Tiempo desde última tarea (bonus para distribuir carga)
        last_task_time = agent.get('last_task_time')
        if last_task_time:
            idle_time = (datetime.now() - last_task_time).seconds
            if idle_time > 300:  # Más de 5 minutos idle
                score += 10
        
        return max(0, score)  # No permitir scores negativos
    
    def _has_similar_context(self, agent_id: str, task: Dict) -> bool:
        """Verifica si el agente tiene contexto similar reciente"""
        if not self.task_history:
            return False
            
        recent_tasks = [t for t in self.task_history 
                       if t['agent_id'] == agent_id 
                       and (datetime.now() - t['timestamp']).seconds < 600]  # últimos 10 min
        
        task_keywords = set(task.get('description', '').lower().split())
        
        for recent in recent_tasks:
            recent_keywords = set(recent['task'].get('description', '').lower().split())
            overlap = len(task_keywords & recent_keywords)
            if overlap > 3:  # Al menos 3 palabras en común
                return True
        
        return False
    
    def report_task_completion(self, agent_id: str, task: Dict, 
                               success: bool, duration: float):
        """Reporta completación de tarea para actualizar estadísticas"""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        
        # Actualizar estadísticas generales
        agent['total_tasks'] += 1
        agent['current_load'] = max(0, agent['current_load'] - 1)
        agent['last_task_time'] = datetime.now()
        
        if success:
            agent['successful_tasks'] += 1
        else:
            agent['failed_tasks'] += 1
        
        # Actualizar duración promedio (media móvil)
        if agent['avg_duration'] == 0:
            agent['avg_duration'] = duration
        else:
            agent['avg_duration'] = (agent['avg_duration'] * 0.8) + (duration * 0.2)
        
        # Actualizar especialización
        task_type = task.get('type', 'general')
        if task_type not in agent['specializations']:
            agent['specializations'][task_type] = {
                'total': 0,
                'successful': 0,
                'avg_duration': 0,
                'success_rate': 0
            }
        
        spec = agent['specializations'][task_type]
        spec['total'] += 1
        if success:
            spec['successful'] += 1
        spec['success_rate'] = spec['successful'] / spec['total']
        spec['avg_duration'] = (spec['avg_duration'] * 0.8) + (duration * 0.2)
        
        # Si está idle, puede volver a recibir tareas
        if agent['current_load'] == 0:
            agent['status'] = 'idle'
        
        # Agregar a historial
        self.task_history.append({
            'agent_id': agent_id,
            'task': task,
            'success': success,
            'duration': duration,
            'timestamp': datetime.now()
        })
    
    def _log_routing_decision(self, task: Dict, selected_agent: str, 
                              all_scores: List[tuple]):
        """Registra decisión de routing para análisis"""
        decision = {
            'timestamp': datetime.now(),
            'task': task,
            'selected_agent': selected_agent,
            'candidate_scores': all_scores
        }
        
        if task['type'] not in self.routing_stats:
            self.routing_stats[task['type']] = []
        
        self.routing_stats[task['type']].append(decision)
    
    def get_agent_recommendations(self, agent_id: str) -> Dict:
        """Genera recomendaciones de mejora para un agente"""
        if agent_id not in self.agents:
            return {}

        agent = self.agents[agent_id]
        recommendations = []
        
        # Analizar tasa de éxito
        if agent['total_tasks'] > 10:
            success_rate = agent['successful_tasks'] / agent['total_tasks']
            if success_rate < 0.7:
                recommendations.append({
                    'type': 'performance',
                    'message': f"Tasa de éxito baja ({success_rate:.1%}). Considerar entrenamiento adicional."
                })
        
        # Analizar velocidad
        if agent['avg_duration'] > 0:
            avg_durations = [a['avg_duration'] for a in self.agents.values() 
                           if a['avg_duration'] > 0]
            if avg_durations:
                median_duration = np.median(avg_durations)
                if agent['avg_duration'] > median_duration * 1.5:
                    recommendations.append({
                        'type': 'speed',
                        'message': f"Duración promedio alta ({agent['avg_duration']:.1f}s vs {median_duration:.1f}s mediana)"
                    })
        
        # Analizar especializaciones
        if not agent['specializations']:
            recommendations.append({
                'type': 'specialization',
                'message': "Sin especializaciones detectadas. Considerar enfocarse en tipos específicos de tareas."
            })
        
        return {
            'agent_id': agent_id,
            'recommendations': recommendations,
            'stats': {
                'total_tasks': agent['total_tasks'],
                'success_rate': agent['successful_tasks'] / agent['total_tasks'] if agent['total_tasks'] > 0 else 0,
                'avg_duration': agent['avg_duration'],
                'specializations': agent['specializations']
            }
        }
    
    def rebalance_load(self) -> List[Dict]:
        """Rebalancea carga entre agentes"""
        actions = []
        
        if not self.agents:
            return []

        # Identificar agentes sobrecargados
        loads = [a['current_load'] for a in self.agents.values()]
        if not loads:
            return []
            
        avg_load = np.mean(loads)
        
        for agent_id, agent in self.agents.items():
            if agent['current_load'] > avg_load * 1.5 and agent['current_load'] > 2:
                actions.append({
                    'action': 'reduce_load',
                    'agent_id': agent_id,
                    'current_load': agent['current_load'],
                    'recommended_load': int(avg_load)
                })
        
        return actions
