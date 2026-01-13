# intelligent_cache.py
import os
import json
import hashlib
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

class IntelligentCache:
    def __init__(self, cache_dir=".antigravity-cache", max_size_mb=500):
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size_mb * 1024 * 1024
        self.db_path = self.cache_dir / "cache_meta.db"
        
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)
            
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            path TEXT,
            size INTEGER,
            created_at REAL,
            last_access REAL,
            access_count INTEGER,
            expires_at REAL,
            context_hash TEXT,
            confidence_score REAL
        )
        ''')
        conn.commit()
        conn.close()
        
    def get(self, key: str, context: Optional[Dict] = None) -> Optional[Any]:
        # Generar key compuesta si hay contexto
        full_key = self._generate_key(key, context)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT path, expires_at, confidence_score FROM cache_entries WHERE key = ?", 
            (full_key,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
            
        path, expires_at, score = row
        
        # Verificar expiración
        if expires_at and datetime.now().timestamp() > expires_at:
            self.invalidate(full_key)
            conn.close()
            return None
            
        # Verificar contexto (si score < umbral, revalidar)
        if context and score < 0.8:
            # Aquí podríamos implementar lógica de revalidación
            pass
            
        # Actualizar acceso
        cursor.execute('''
        UPDATE cache_entries 
        SET last_access = ?, access_count = access_count + 1 
        WHERE key = ?
        ''', (datetime.now().timestamp(), full_key))
        conn.commit()
        conn.close()
        
        # Leer archivo
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return None
            
    def set(self, key: str, value: Any, context: Optional[Dict] = None, 
            ttl: int = 3600, confidence: float = 1.0):
        
        full_key = self._generate_key(key, context)
        content = json.dumps(value)
        size = len(content)
        
        # Enforce size limit (simple eviction)
        self._enforce_size_limit(size)
        
        # Guardar archivo
        file_path = self.cache_dir / f"{hashlib.md5(full_key.encode()).hexdigest()}.json"
        with open(file_path, 'w') as f:
            f.write(content)
            
        # Guardar metadata
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().timestamp()
        expires = now + ttl
        
        cursor.execute('''
        INSERT OR REPLACE INTO cache_entries 
        (key, path, size, created_at, last_access, access_count, expires_at, context_hash, confidence_score)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        ''', (
            full_key, str(file_path), size, now, now, expires, 
            self._context_hash(context), confidence
        ))
        
        conn.commit()
        conn.close()
        
    def invalidate(self, key: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM cache_entries WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row and os.path.exists(row[0]):
            os.remove(row[0])
            
        cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        
    def _generate_key(self, key: str, context: Optional[Dict]) -> str:
        if not context:
            return key
        return f"{key}::{self._context_hash(context)}"
        
    def _context_hash(self, context: Optional[Dict]) -> str:
        if not context:
            return "global"
        # Simplificación: hashear keys ordenadas
        c_str = json.dumps(context, sort_keys=True)
        return hashlib.md5(c_str.encode()).hexdigest()
        
    def _enforce_size_limit(self, new_size: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(size) FROM cache_entries")
        current_size = cursor.fetchone()[0] or 0
        
        while current_size + new_size > self.max_size:
            # Evict LRU
            cursor.execute("SELECT key, path, size FROM cache_entries ORDER BY last_access ASC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                break
                
            self.invalidate(row[0])
            current_size -= row[2]
            
        conn.close()
