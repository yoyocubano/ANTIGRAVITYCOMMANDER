# maintenance.py
import os
import sys
import sqlite3
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Configuración
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = BASE_DIR.parent / ".antigravity-cache"
OUTPUT_LOGS = BASE_DIR.parent / "logs"
DB_PATH = BASE_DIR / "antigravity-memory.db"

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def cleanup_cache():
    """Limpia archivos de caché antiguos"""
    log("🧹 Iniciando limpieza de caché...")
    
    if not CACHE_DIR.exists():
        log("No hay directorio de caché.")
        return

    # Limpiar archivos .json antiguos (> 7 días no accedidos)
    cleaned_count = 0
    size_freed = 0
    
    # Conectar a la DB de caché para consistencia
    cache_meta_db = CACHE_DIR / "cache_meta.db"
    if cache_meta_db.exists():
        try:
            conn = sqlite3.connect(cache_meta_db)
            cursor = conn.cursor()
            
            # Borrar entradas expiradas
            cursor.execute("SELECT path FROM cache_entries WHERE expires_at < ?", (time.time(),))
            rows = cursor.fetchall()
            
            for row in rows:
                path = Path(row[0])
                if path.exists():
                    size_freed += path.stat().st_size
                    path.unlink()
                    cleaned_count += 1
            
            cursor.execute("DELETE FROM cache_entries WHERE expires_at < ?", (time.time(),))
            conn.commit()
            
            # Vacuum para recuperar espacio
            cursor.execute("VACUUM")
            conn.close()
            log(f"Caché optimizada: {cleaned_count} archivos eliminados, {size_freed/1024/1024:.2f} MB liberados.")
        except Exception as e:
            log(f"Error limpiando DB de caché: {e}")
            
def optimize_memory_db():
    """Optimiza la base de datos de memoria persistente"""
    log("🧠 Optimizando memoria persistente...")
    
    if not DB_PATH.exists():
        log("No hay base de datos de memoria.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Eliminar tareas muy antiguas (> 30 días) excepto hitos importantes
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("DELETE FROM task_history WHERE start_time < ? AND status != 'failed'", (thirty_days_ago,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        # Reconstruir índices y compactar
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        
        conn.close()
        log(f"Memoria optimizada: {deleted_count} registros antiguos purgados.")
    except Exception as e:
        log(f"Error optimizando memoria: {e}")

def rotate_logs():
    """Rota y comprime logs antiguos"""
    log("📝 Rotando logs del sistema...")
    
    if not OUTPUT_LOGS.exists():
        return
        
    for log_file in OUTPUT_LOGS.glob("*.log"):
        # Si es mayor a 10MB o más antiguo de 24h
        if log_file.stat().st_size > 10 * 1024 * 1024:
            # Aquí podríamos comprimir, por ahora solo renombramos timestamp
            params = datetime.now().strftime("%Y%m%d%H%M%S")
            new_name = log_file.with_name(f"{log_file.stem}_{params}.log.old")
            log_file.rename(new_name)
            log(f"Log rotado: {log_file.name} -> {new_name.name}")

def main():
    log("=== EJECUTANDO MANTENIMIENTO NOCTURNO (3:00 AM) ===")
    
    cleanup_cache()
    optimize_memory_db()
    rotate_logs()
    
    log("=== MANTENIMIENTO COMPLETADO ===")

if __name__ == "__main__":
    main()
