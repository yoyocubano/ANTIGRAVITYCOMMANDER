# telemetry.py
import time
from datetime import datetime
from collections import defaultdict, deque
import statistics
import json
from typing import Dict, List

class TelemetrySystem:
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'count': 0,
            'sum': 0,
            'min': float('inf'),
            'max': float('-inf'),
            'values': deque(maxlen=1000)  # Últimos 1000 valores
        })
        
        self.events = deque(maxlen=10000)  # Últimos 10000 eventos
        self.alerts = []
        self.thresholds = {}
        
    def record_metric(self, name: str, value: float, tags: Dict = None):
        """Registra una métrica"""
        metric = self.metrics[name]
        
        metric['count'] += 1
        metric['sum'] += value
        metric['min'] = min(metric['min'], value)
        metric['max'] = max(metric['max'], value)
        metric['values'].append({
            'value': value,
            'timestamp': time.time(),
            'tags': tags or {}
        })
        
        # Verificar alertas
        self._check_thresholds(name, value)
    
    def record_event(self, event_type: str, details: Dict):
        """Registra un evento"""
        self.events.append({
            'type': event_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_metric_summary(self, name: str, time_window: int = None) -> Dict:
        """Obtiene resumen de métrica"""
        if name not in self.metrics:
            return None
        
        metric = self.metrics[name]
        values = list(metric['values'])
        
        # Filtrar por ventana de tiempo si se especifica
        if time_window:
            cutoff = time.time() - time_window
            values = [v for v in values if v['timestamp'] > cutoff]
        
        if not values:
            return None
        
        numeric_values = [v['value'] for v in values]
        
        return {
            'name': name,
            'count': len(values),
            'sum': sum(numeric_values),
            'mean': statistics.mean(numeric_values),
            'median': statistics.median(numeric_values),
            'std_dev': statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0,
            'min': min(numeric_values),
            'max': max(numeric_values),
            'p95': self._percentile(numeric_values, 95),
            'p99': self._percentile(numeric_values, 99)
        }
    
    def set_threshold(self, metric_name: str, threshold_type: str, 
                     value: float, alert_message: str):
        """Establece umbral para alertas"""
        self.thresholds[metric_name] = {
            'type': threshold_type,  # 'max', 'min', 'avg'
            'value': value,
            'message': alert_message
        }
    
    def _check_thresholds(self, metric_name: str, value: float):
        """Verifica umbrales y genera alertas"""
        if metric_name not in self.thresholds:
            return
        
        threshold = self.thresholds[metric_name]
        triggered = False
        
        if threshold['type'] == 'max' and value > threshold['value']:
            triggered = True
        elif threshold['type'] == 'min' and value < threshold['value']:
            triggered = True
        elif threshold['type'] == 'avg':
            summary = self.get_metric_summary(metric_name, time_window=300)
            if summary and summary['mean'] > threshold['value']:
                triggered = True
        
        if triggered:
            alert = {
                'metric': metric_name,
                'value': value,
                'threshold': threshold['value'],
                'message': threshold['message'],
                'timestamp': datetime.now().isoformat()
            }
            self.alerts.append(alert)
            print(f"🚨 ALERTA: {threshold['message']} (valor: {value})")
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calcula percentil"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_dashboard_data(self) -> Dict:
        """Obtiene datos para dashboard"""
        return {
            'metrics': {
                name: self.get_metric_summary(name, time_window=3600)
                for name in self.metrics.keys()
            },
            'recent_events': list(self.events)[-100:],
            'active_alerts': self.alerts[-10:],
            'timestamp': datetime.now().isoformat()
        }
    
    def export_metrics(self, format: str = 'prometheus') -> str:
        """Exporta métricas en formato estándar"""
        if format == 'prometheus':
            lines = []
            for name, metric in self.metrics.items():
                summary = self.get_metric_summary(name)
                if summary:
                    lines.append(f"# HELP {name} Metric {name}")
                    lines.append(f"# TYPE {name} gauge")
                    lines.append(f"{name}{{stat=\"mean\"}} {summary['mean']}")
                    lines.append(f"{name}{{stat=\"max\"}} {summary['max']}")
                    lines.append(f"{name}{{stat=\"min\"}} {summary['min']}")
            return "\n".join(lines)
        
        return json.dumps(self.get_dashboard_data(), indent=2)


# Decorador para instrumentar funciones
def monitor(metric_name: str = None, telemetry: TelemetrySystem = None):
    """Decorador para monitorear ejecución de funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                if telemetry:
                    telemetry.record_metric(f"{name}.duration", duration)
                    telemetry.record_metric(f"{name}.success", 1)
                    telemetry.record_event('function_call', {
                        'function': name,
                        'duration': duration,
                        'status': 'success'
                    })
                
                return result
            
            except Exception as e:
                duration = time.time() - start
                
                if telemetry:
                    telemetry.record_metric(f"{name}.error", 1)
                    telemetry.record_event('function_error', {
                        'function': name,
                        'error': str(e),
                        'duration': duration
                    })
                
                raise
        
        return wrapper
    return decorator


# Sistema de Logging Estructurado
class StructuredLogger:
    def __init__(self, agent_id: str, telemetry: TelemetrySystem):
        self.agent_id = agent_id
        self.telemetry = telemetry
        
    def log(self, level: str, message: str, **kwargs):
        """Log estructurado"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id,
            'level': level,
            'message': message,
            **kwargs
        }
        
        print(f"[{level}] [{self.agent_id}] {message}")
        
        self.telemetry.record_event(f"log.{level}", log_entry)
        
        if level == 'ERROR':
            self.telemetry.record_metric(f"errors.{self.agent_id}", 1)
    
    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log('DEBUG', message, **kwargs)
