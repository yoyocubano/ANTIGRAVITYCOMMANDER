# 📋 MASTER PLAN: Migración a Arquitectura Nube Híbrida (Rentabilizando Render)

Este documento detalla la hoja de ruta para migrar tus proyectos principales a la arquitectura escalable **Render + Cloudflare + Supabase**.

## 🏗️ Arquitectura Objetivo

* **Frontend:** Cloudflare Pages (Gratis, Rápido, Global).
* **Backend:** Render Web Services (Pago/Gratis, Python/Node, Lógica pesada).
* **Base de Datos:** Supabase (PostgreSQL) o Appwrite.
* **Conectividad:** Cloudflare Tunnels & Workers (Seguridad y Routing).
* **Control:** GitHub CI/CD (Automatización total).

---

## 🚀 FASE 1: Piloto (AntiGravity Commander)

El objetivo es dejar este proyecto 100% funcional en la nube como prueba de concepto.

* [x] **Reestructuración de Repositorio**
  * [x] Separar `/backend` y `/frontend`.
  * [x] Configurar `requirements.txt` y `Procfile` para Render.
  * [x] Configurar `wrangler.toml` para Cloudflare.

* [ ] **Despliegue Backend (Render)**
  * [ ] Realizar despliegue manual/automático en Render.
  * [ ] Obtener URL de producción (`https://antigravity-commander.onrender.com`).
  * [ ] Verificar logs de arranque (sin errores de puertos o `requirements`).

* [ ] **Despliegue Frontend (Cloudflare Pages)**
  * [ ] Conectar repo a Cloudflare Pages.
  * [ ] Configurar variables de entorno (URL del Backend).
  * [ ] Inyectar URL del Backend en `index.html` (para reemplazar `localhost`).

* [ ] **Validación Final**
  * [ ] Verificar conexión WebSocket Frontend -> Backend Nube.
  * [ ] Probar persistencia de datos básica.

---

## 🔄 FASE 2: Estandarización de Proyectos (WeLuxEvents, etc.)

Aplicar la misma estructura a tus proyectos comerciales.

* [ ] **Auditoría de Proyectos**
  * [ ] Identificar qué partes son estáticas (HTML/React) y cuáles dinámicas (Python/Node).
  * [ ] Revisar dependencias de Base de Datos (SQLite -> PostgreSQL/Supabase).

* [ ] **Adaptación de Código (Backend)**
  * [ ] Migrar SQLite a Supabase (usando `psycopg2` o cliente Supabase Python).
  * [ ] Configurar `gunicorn` para producción (no usar `flask run`).
  * [ ] Implementar manejo de errores para conexiones de DB (Connection Pooling).

* [ ] **Optimización de Base de Datos (Supabase)**
  * [ ] Configurar Connection Pooling (PgBouncer) para compatibilidad con Render (IPv4).
  * [ ] Definir políticas RLS (Row Level Security) si hay autenticación.

* [ ] **Automatización (CI/CD)**
  * [ ] Crear GitHub Action para despliegue automático a Render (Deploy Hooks).
  * [ ] Crear GitHub Action para validación de código (Linting/Tests).

---

## ☁️ FASE 3: Capa de Inteligencia (Cloudflare)

Aprovechar el poder de Cloudflare para proteger y acelerar.

* [ ] **Workers Layer**
  * [ ] Crear Worker "Router" para manejar peticiones API vs Estáticas.
  * [ ] Implementar caché de borde para respuestas API comunes.

* [ ] **Seguridad (Tunnels)**
  * [ ] Configurar `cloudflared` para servicios internos que no deben ser públicos.
  * [ ] Proteger paneles administrativos con Cloudflare Access (Login agnóstico).

---

## 🛠️ Tareas Técnicas Inmediatas (Para Copiar/Pegar)

### 1. Conectar Frontend a Backend de Render

Modificar el JS del frontend para detectar el entorno:

```javascript
// frontend/index.html (Snippet)
const BACKEND_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8765' 
    : 'https://TU-APP-EN-RENDER.onrender.com';
const socket = io(BACKEND_URL);
```

### 2. Configurar Supabase en Python (Render)

Instalar cliente: `pip install supabase`

```python
# backend/database.py
import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
```
