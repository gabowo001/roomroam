# Plan: Instalar, arrancar RoomRoam y exponerlo con cloudflared

## Contexto
- Monorepo RoomRoam: `frontend/` (React 18 + TS + Vite, puerto 3000) y `backend/` (Quart + Hypercorn, puerto 5000, requiere PostgreSQL).
- Entorno del contenedor (verificado): Node/npm instalados; **faltan** python3, pip, PostgreSQL y cloudflared. Somos root con `apt` disponible. Red saliente disponible (curl/wget).
- Bloqueo funcional: `frontend/src/services/websocketManager.ts:24` conecta a `${protocol}//${hostname}:5000/ws`. Por el túnel solo se expone el puerto 3000 → WS roto. **Usuario aprobó** corregirlo para usar el proxy `/ws` de Vite (mismo origen).

## Pasos (agente de implementación)

### 1. Paquetes de sistema
```bash
apt-get update
apt-get install -y python3 python3-venv python3-pip postgresql
```
- Arrancar PostgreSQL: `pg_lsclusters` para ver versión/cluster, luego `pg_ctlcluster <ver> main start` (o `service postgresql start`).
- Crear rol y BD (como root via `su postgres -c`):
  ```bash
  su postgres -c "psql -c \"CREATE USER roomroam WITH PASSWORD 'roomroam_dev';\""
  su postgres -c "createdb roomroam -O roomroam"
  ```
- Verificar: `su postgres -c "psql -c 'SELECT 1;'"`

### 2. Backend
- `cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- Crear `backend/.env` (copiar de `.env.example`):
  ```dotenv
  DEBUG=True
  PORT=5000
  DATABASE_URL=postgresql://roomroam:roomroam_dev@localhost:5432/roomroam
  SECRET_KEY=<generado con python -c 'import secrets; print(secrets.token_hex(32))'>
  ```
- Arrancar en segundo plano con log: `nohup python app.py > /tmp/backend.log 2>&1 &`
- Validar: `curl http://localhost:5000/api/test` → `{"success": true, ...}` (crea tablas en el primer arranque).

### 3. Fix WebSocket (único cambio de código, aprobado por el usuario)
En `frontend/src/services/websocketManager.ts` (línea 24), reemplazar:
```ts
const wsUrl = `${protocol}//${window.location.hostname}:5000/ws`;
```
por:
```ts
const wsUrl = `${protocol}//${window.location.host}/ws`;
```
(mismo origen → proxy `/ws` de Vite con `ws: true`, y cloudflared soporta WebSockets).

### 4. Frontend
- `cd frontend && npm install`
- Arrancar: `nohup npm run dev > /tmp/frontend.log 2>&1 &`
- Confirmar en el log que escucha en el puerto 3000; validar `curl -s http://localhost:3000 | head` devuelve HTML.
- Validar proxy: `curl http://localhost:3000/api/test` → respuesta del backend.

### 5. cloudflared
- Instalar binario:
  ```bash
  curl -L -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /usr/local/bin/cloudflared
  ```
- Arrancar quick tunnel: `nohup cloudflared tunnel --url http://localhost:3000 > /tmp/cloudflared.log 2>&1 &`
- Extraer la URL `https://<random>.trycloudflare.com` de `/tmp/cloudflared.log` (línea "Your quick Tunnel has been created").

### 6. Validación final
- `curl -s <URL_TUNNEL>` → HTML del frontend (200).
- `curl <URL_TUNNEL>/api/test` → `{"success": true, ...}` (proxy Vite funcionando vía túnel).
- Reportar la URL pública al usuario. Nota: la conexión WS completa requiere navegador; no hay que hacer más cambios (proxy + túnel la soportan).

## Riesgos / Notas
- Si no hay red saliente para apt/curl, reportarlo y detenerse.
- La URL de quick tunnel es **efímera**: caduca al terminar la sesión del contenedor.
- Backend single-process (WS rooms en memoria) — no escalar procesos.
- No ejecutar `reset_db.py` ni `test_*.py` (borran/escriben datos).

## Entregable
URL pública `https://...trycloudflare.com` apuntando al frontend en :3000, con API y WebSocket funcionando a través del mismo origen.
