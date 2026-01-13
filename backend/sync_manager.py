# sync_manager.py
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Any
import hashlib

class SyncManager:
    def __init__(self):
        self.shared_context = {}
        self.context_history = []
        self.subscriptions = {}
        self.conflict_resolution = 'last_write_wins'
        # Lazy initialization of Queue to ensure it attaches to the correct loop
        self.sync_queue = None
        
    def _ensure_queue(self):
        if self.sync_queue is None:
            self.sync_queue = asyncio.Queue()

    async def update_context(self, agent_id: str, context_key: str, 
                            value: Any, metadata: Dict = None):
        self._ensure_queue()
        timestamp = datetime.now()
        
        if context_key in self.shared_context:
            existing = self.shared_context[context_key]
            if self._has_conflict(existing, value, timestamp):
                value = await self._resolve_conflict(existing, value, agent_id, timestamp)
        
        self.shared_context[context_key] = {
            'value': value,
            'updated_by': agent_id,
            'timestamp': timestamp.isoformat(),
            'version': self._get_next_version(context_key),
            'metadata': metadata or {},
            'checksum': self._calculate_checksum(value)
        }
        
        self.context_history.append({
            'key': context_key,
            'value': value,
            'agent': agent_id,
            'timestamp': timestamp.isoformat(),
            'action': 'update'
        })
        
        await self._notify_subscribers(context_key, agent_id)
        return self.shared_context[context_key]
    
    def subscribe(self, agent_id: str, context_keys: List[str]):
        if agent_id not in self.subscriptions:
            self.subscriptions[agent_id] = set()
        self.subscriptions[agent_id].update(context_keys)
    
    async def _notify_subscribers(self, context_key: str, updater_agent: str):
        self._ensure_queue()
        for agent_id, subscribed_keys in self.subscriptions.items():
            if context_key in subscribed_keys and agent_id != updater_agent:
                await self.sync_queue.put({
                    'type': 'CONTEXT_UPDATE',
                    'target_agent': agent_id,
                    'context_key': context_key,
                    'value': self.shared_context[context_key],
                    'updated_by': updater_agent
                })
    
    def get_context(self, context_key: str, agent_id: str = None) -> Dict:
        if context_key not in self.shared_context: return None
        context = self.shared_context[context_key]
        if not self._verify_checksum(context): return None
        return context
    
    def _has_conflict(self, existing: Dict, new_value: Any, timestamp: datetime) -> bool:
        existing_time = datetime.fromisoformat(existing['timestamp'])
        possible_conflict = (timestamp - existing_time).total_seconds() < 1
        return possible_conflict and existing['value'] != new_value
    
    async def _resolve_conflict(self, existing: Dict, new_value: Any, agent_id: str, timestamp: datetime) -> Any:
        return new_value
    
    def _calculate_checksum(self, value: Any) -> str:
        serialized = json.dumps(value, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _verify_checksum(self, context: Dict) -> bool:
        expected = context.get('checksum')
        if not expected: return True
        return self._calculate_checksum(context['value']) == expected
    
    def _get_next_version(self, context_key: str) -> int:
        return self.shared_context[context_key].get('version', 0) + 1 if context_key in self.shared_context else 1
    
    async def start_sync_worker(self):
        self._ensure_queue()
        while True:
            try:
                msg = await self.sync_queue.get()
                # Simulate processing
                await asyncio.sleep(0.01)
                self.sync_queue.task_done()
            except Exception as e:
                print(f"Sync error: {e}")

class DistributedCache:
    def __init__(self, sync_manager: SyncManager):
        self.sync = sync_manager
        self.local_caches = {}
        
    def register_agent_cache(self, agent_id: str):
        self.local_caches[agent_id] = {'data': {}, 'hits': 0, 'misses': 0}
    
    async def get(self, agent_id: str, key: str) -> Any:
        if agent_id in self.local_caches:
            local = self.local_caches[agent_id]
            if key in local['data']:
                local['hits'] += 1
                return local['data'][key]
            local['misses'] += 1
        
        shared = self.sync.get_context(key)
        if shared:
            if agent_id in self.local_caches:
                self.local_caches[agent_id]['data'][key] = shared['value']
            return shared['value']
        return None
    
    async def set(self, agent_id: str, key: str, value: Any, ttl: int = 3600, shared: bool = True):
        if agent_id in self.local_caches:
            self.local_caches[agent_id]['data'][key] = value
        if shared:
            await self.sync.update_context(agent_id, key, value, {'ttl': ttl})
