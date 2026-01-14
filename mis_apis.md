# 📘 GUÍA COMPLETA: Render.com - APIs, Túneles, Optimizaciones e Integraciones

## 🔌 APIs DE RENDER - Documentación Completa

### API REST Oficial

**Base URL**: `https://api.render.com/v1`[1]

**Autenticación**: Bearer Token (API Key)

```bash
Authorization: Bearer {{tu_render_api_key}}
```

### Endpoints Principales Disponibles:[2][1]

#### 1. **Servicios y Datastores**

- `GET /services` - Listar todos los servicios
- `POST /services` - Crear nuevo servicio
- `GET /services/{serviceId}` - Obtener detalles de servicio
- `PATCH /services/{serviceId}` - Actualizar servicio
- `DELETE /services/{serviceId}` - Eliminar servicio

#### 2. **Despliegues (Deploys)**

- `GET /services/{serviceId}/deploys` - Listar despliegues
- `POST /services/{serviceId}/deploys` - Crear despliegue
- `GET /deploys/{deployId}` - Estado de despliegue

#### 3. **Variables de Entorno**

- `GET /services/{serviceId}/env-vars` - Listar variables
- `PUT /services/{serviceId}/env-vars` - Actualizar variables[3]

#### 4. **Métricas y Logs**

- `GET /services/{serviceId}/metrics` - Obtener métricas
- `GET /services/{serviceId}/logs` - Stream de logs

#### 5. **Dominios Personalizados**

- `GET /services/{serviceId}/custom-domains` - Listar dominios
- `POST /services/{serviceId}/custom-domains` - Añadir dominio

#### 6. **Jobs One-off**

- `POST /services/{serviceId}/jobs` - Ejecutar trabajo puntual

#### 7. **Blueprints (IaC)**

- `POST /blueprints` - Crear blueprint desde render.yaml

#### 8. **Audit Logs**

- `GET /audit-logs` - Registro de auditoría

### OpenAPI Spec

**URL**: `https://api-docs.render.com/openapi/6140fb3daeae351056086186`[1]

***

## 🌐 TÚNELES Y CONEXIONES PRIVADAS CON RENDER

### 1. **Private Network (Red Privada Interna)**[4]

**Características**:

- Comunicación entre servicios en la **misma región** sin internet público
- Hostnames internos estables: `{service-name}.{region}.render.internal`
- IPs internas dinámicas que mapean automáticamente

**Ejemplo de conexión**:

```python
# Desde un web service a otro servicio privado
DATABASE_URL = "postgresql://elastic-qeqj:5432/mydb"
REDIS_URL = "redis://redis-abc123:6379"
API_INTERNAL = "http://backend-api.oregon.render.internal:8000"
```

**Limitaciones**:

- Máximo 75 puertos abiertos por servicio
- Puertos prohibidos: 10000, 18012, 18013, 19099[4]
- Servicios **Free** pueden **enviar** pero NO **recibir** tráfico privado
- Background workers y cron jobs solo pueden enviar, no recibir

**Casos de uso**:

- Microservicios backend comunicándose entre sí
- Web service → Private service (API interna)
- Web service → PostgreSQL/Redis via URL interna
- Worker → Database para procesamiento batch

### 2. **Private Link (Conexión Externa Privada)**[1]

Para conectar Render con sistemas **NO-Render** (AWS, GCP, on-premise):

- Requiere plan Enterprise
- VPN site-to-site con servicios externos
- Sin pasar por internet público

### 3. **Proxy/Túnel con Cloudflare**[5]

**Configuración Orange-to-Orange**:

```
Cliente → Cloudflare CDN → Cloudflare Worker → Render Service
```

- Usa CNAME records apuntando a tu `.onrender.com`
- Worker override para routing inteligente
- SSL/TLS end-to-end

### 4. **Métodos de Conexión Externos**

**Opción A: Deploy Hooks (HTTP Trigger)**[6]

```bash
# Trigger desde GitHub Actions, CI/CD o CMS
curl -X POST https://api.render.com/deploy/srv-xxxxx?key=SECRET_KEY
```

**Opción B: Webhooks (Event Listener)**[7]

- Render envía eventos HTTP POST a tu endpoint cuando:
  - `build_started`, `build_ended`
  - `deploy_started`, `deploy_ended`
  - `service_scaled`, `service_suspended`

**Opción C: SSH/Shell Access**[1]

```bash
render ssh {service-name}
```

***

## ☁️ OPTIMIZACIONES: CLOUDFLARE + RENDER

### 1. **Configuración DNS Óptima**[5]

```dns
# CNAME Records
@ → tu-app.onrender.com (Orange cloud)
www → tu-app.onrender.com (Orange cloud)
* → tu-app.onrender.com (Grey cloud solo si usas wildcard)
```

**SSL/TLS Settings**:

- Mode: **Full (strict)** o **Full**
- Universal SSL activo
- Edge Certificates con Let's Encrypt

### 2. **Cloudflare Workers para Edge Routing**[5]

```javascript
// Worker que redirige tráfico a Render
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  url.hostname = 'tu-app.onrender.com'
  return fetch(url, request)
}
```
