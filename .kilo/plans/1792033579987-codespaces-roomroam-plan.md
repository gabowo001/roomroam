# Plan: QA manual de RoomRoam en GitHub Codespaces (devcontainer + docker-compose)

## Objetivo
Configurar `gabowo001/roomroam` para QA manual desde navegador vía GitHub Codespaces, accesible solo a `gabowo001`, con una única URL HTTPS del frontend que sirva la app completa (`/api` y `/ws` proxied al backend), PostgreSQL interno, secretos fuera de Git y scripts idempotentes de arranque/parada. Subir a la rama actual y, si las credenciales lo permiten, crear el Codespace (2 núcleos, idle 10 min).

## Hechos verificados (no volver a comprobar salvo para confirmar)
- Rama actual y de trabajo: `kilo/steep-velvet-t9n` (HEAD `5d6613e`, up to date con `origin/kilo/steep-velvet-t9n`). Remoto: `https://github.com/gabowo001/roomroam.git`.
- Repo `gabowo001/roomroam` es **público** (`gh repo view`). Por eso la visibilidad de puertos **debe forzarse a Private** (los repos públicos tienden a `public`).
- `gh` está autenticado como `kilo-code-bot[bot]` con `GH_TOKEN` de GitHub App. `gh codespace list` y `GET /user` devuelven **HTTP 403 "Resource not accessible by integration"**. Conclusión: **las credenciales disponibles NO permiten crear el Codespace ni acceder a la cuenta** → requisito 5 se entrega como paso manual.
- El repo API devuelve `permissions.push=false` para el token, aunque la rama ya existe en origin. **Riesgo**: verificar que `git push` funcione; si falla, entregar el diff y el paso manual.
- Frontend ya usa rutas relativas `/api/...` en `Chat.tsx` y `Login.tsx`, y `websocketManager.ts:24` ya usa `${protocol}//${window.location.host}/ws` (mismo origen). **No hay más `:5000` en `frontend/src`.**
- `frontend/vite.config.ts` ya tiene `host:'0.0.0.0'`, `allowedHosts:true` y proxies `/api`→`http://127.0.0.1:5000`, `/ws`→`ws://127.0.0.1:5000` (`ws:true`).
- `backend/app.py` bindea `0.0.0.0:5000` y `QUART_AUTH_COOKIE_SECURE=False`; `app.before_request` y el WS **imprimen cabeceras y cookies** (fuga de secretos en logs).
- Sandbox de implementación: hay `node`, `npm`, `apt-get`, `git`, `gh`; **no** hay `python3`, `psql`, `docker`. No se puede probar el stack compose aquí.
- Restricciones de tooling: comandos bash con `|`, `;`, `&`, `>` están bloqueados por política; usar comandos simples o `workdir`.

## Decisiones de diseño
- **Docker Compose con 2 servicios** (elección del usuario): `app` (devcontainer: Node 20 + Python 3) y `db` (`postgres:16` con volumen nombrado). El backend y el frontend corren como procesos dentro de `app` (hot reload), gestionados por scripts idempotentes con pidfiles.
- **Red compose por defecto**: `app` alcanza Postgres en `db:5432`. Solo se reenvía el puerto **3000** (`forwardPorts`). Backend escucha en `127.0.0.1:5000` dentro de `app` (no reenviable). `db` no publica puertos.
- **Una sola URL**: el navegador solo ve `https://<CODESPACE>-3000.app.github.dev`; Vite sirve el frontend y proxya `/api` y `/ws` a `127.0.0.1:5000`. WSS y cookies son del mismo origen.
- **Cookies HTTPS**: `COOKIE_SECURE=true` en el devcontainer (Codespaces sirve HTTPS). `SameSite=Lax` (mismo origen). Se controla por variable de entorno.
- **Secretos fuera de Git**: `initializeCommand` genera `.devcontainer/.env` (password de Postgres) y `backend/.env` (`SECRET_KEY`, `DATABASE_URL`, etc.) solo si no existen; ambos quedan en `.gitignore`. Valores hex aleatorios → no requieren percent-encoding.
- **Visibilidad Private**: `devcontainer.json` no soporta `visibility` (spec + schema de Codespaces no lo incluyen). Se fuerza en `start.sh` con `gh codespace ports visibility 3000:private -c "$CODESPACE_NAME"` (con reintentos), más paso manual documentado.
- **Persistencia**: volumen nombrado `roomroam-pgdata` → los datos sobreviven a stop/start del Codespace; se pierden solo en Rebuild. `.venv` y `node_modules` viven en el workspace bind-mounted → persisten.

## Tareas de implementación (orden)

### 1. Crear `.devcontainer/Dockerfile`
Base con Node 20 y añadir Python 3 + cliente Postgres:
```dockerfile
FROM mcr.microsoft.com/devcontainers/typescript-node:20-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip postgresql-client \
 && rm -rf /var/lib/apt/lists/*
```

### 2. Crear `.devcontainer/docker-compose.yml`
```yaml
services:
  app:
    build:
      context: ..
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - ..:/workspaces/roomroam:cached
    command: sleep infinity
    depends_on:
      db:
        condition: service_healthy
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-roomroam}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-roomroam_dev}
      POSTGRES_DB: ${POSTGRES_DB:-roomroam_dev}
    volumes:
      - roomroam-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-roomroam} -d ${POSTGRES_DB:-roomroam_dev}"]
      interval: 5s
      timeout: 5s
      retries: 10
volumes:
  roomroam-pgdata:
    name: roomroam-pgdata
```
Notas: compose carga automáticamente `.devcontainer/.env` (mismo directorio que el compose). **No** añadir `ports:` (no se publican puertos internos).

### 3. Crear `.devcontainer/devcontainer.json`
```jsonc
{
  "name": "RoomRoam (Codespaces)",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspaces/roomroam",
  "shutdownAction": "stopCompose",
  "remoteUser": "node",
  "initializeCommand": "bash .devcontainer/scripts/init-secrets.sh",
  "postCreateCommand": "bash .devcontainer/scripts/setup.sh",
  "postStartCommand": "bash .devcontainer/scripts/start.sh",
  "forwardPorts": [3000],
  "portsAttributes": {
    "3000": { "label": "RoomRoam (frontend)", "onAutoForward": "notify" }
  },
  "otherPortsAttributes": { "onAutoForward": "ignore" },
  "customizations": {
    "vscode": { "extensions": ["ms-python.python", "dbaeumer.vscode-eslint"] }
  }
}
```
`otherPortsAttributes.onAutoForward=ignore` evita reenviar 5000/5432 si algo los expone.

### 4. Crear `.devcontainer/scripts/init-secrets.sh` (host, idempotente)
Genera secretos solo si faltan; usa `SECRET_KEY`/`POSTGRES_PASSWORD` del entorno si existen (permite Codespaces secrets):
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DC_ENV="$ROOT/.devcontainer/.env"
BE_ENV="$ROOT/backend/.env"
gen() { openssl rand -hex 32 2>/dev/null || head -c32 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
if [ ! -f "$DC_ENV" ]; then
  printf 'POSTGRES_USER=%s\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=%s\n' \
    "${POSTGRES_USER:-roomroam}" "${POSTGRES_PASSWORD:-$(gen)}" "${POSTGRES_DB:-roomroam_dev}" > "$DC_ENV"
fi
set -a; . "$DC_ENV"; set +a
if [ ! -f "$BE_ENV" ]; then
  cat > "$BE_ENV" <<EOF
DEBUG=True
HOST=127.0.0.1
PORT=5000
COOKIE_SECURE=true
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
SECRET_KEY=${SECRET_KEY:-$(gen)}
EOF
fi
```

### 5. Crear `.devcontainer/scripts/setup.sh` (postCreate)
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="/workspaces/roomroam"
cd "$ROOT/backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd "$ROOT/frontend"
npm install
```

### 6. Crear `.devcontainer/scripts/start.sh` (postStart y uso manual; idempotente)
- Espera `pg_isready -h db -p 5432` (máx ~60s).
- Arranca backend solo si 5000 no responde: `nohup .venv/bin/python app.py >> logs/backend.log 2>&1 &` + pidfile.
- Arranca frontend solo si 3000 no responde: `nohup npm run dev -- --host 0.0.0.0 --port 3000 --strictPort >> logs/frontend.log 2>&1 &` + pidfile.
- Fuerza visibilidad privada:
```bash
if [ -n "${CODESPACE_NAME:-}" ] && command -v gh >/dev/null 2>&1; then
  for i in 1 2 3 4 5; do
    GH_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}" gh codespace ports visibility 3000:private -c "$CODESPACE_NAME" && break
    sleep $((i*2))
  done
fi
```
- Imprime la URL `https://$CODESPACE_NAME-3000.app.github.dev`.

### 7. Crear `.devcontainer/scripts/stop.sh` y `restart.sh`
- `stop.sh`: mata por pidfile (`kill $(cat logs/*.pid)`), borra pidfiles; fallback `pkill -f 'app.py'`/`pkill -f vite` acotado. No toca `db`.
- `restart.sh`: `stop.sh` y luego `start.sh`.

### 8. Modificar `backend/app.py`
- `HOST = os.environ.get('HOST', '127.0.0.1')`; `config.bind = [f"{HOST}:{port}"]`.
- `app.config['QUART_AUTH_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', 'false').lower() in ('1','true','yes')`.
- Mantener `QUART_AUTH_COOKIE_SAMESITE='Lax'`.
- Reducir logs: quitar impresión de `Headers`/`Cookies` en `log_request` y en el WS (evita filtrar cookies de sesión).

### 9. Modificar `frontend/vite.config.ts`
Añadir HMR para Codespaces (la página es HTTPS; evita mixed-content en el WS de HMR) y `strictPort`:
```ts
const codespaces = !!process.env.CODESPACES
// server: { host:'0.0.0.0', port:3000, strictPort:true, allowedHosts:true,
//   hmr: codespaces ? { protocol:'wss', clientPort:443 } : undefined,
//   proxy: { '/api': {...127.0.0.1:5000}, '/ws': { target:'ws://127.0.0.1:5000', ws:true, changeOrigin:true } } }
```
(vite.config.ts no lo type-checkea `tsc` porque `tsconfig.json` incluye solo `src`; `process.env` es seguro.)

### 10. Actualizar `backend/.env.example`
Añadir/actualizar `HOST=127.0.0.1` y `COOKIE_SECURE=true` con comentario de uso en Codespaces. `DATABASE_URL` de ejemplo puede quedar con `localhost` para uso local.

### 11. Actualizar `.gitignore`
En raíz, asegurar que no se suban secretos/artefactos:
```
.devcontainer/.env
.devcontainer/logs/
*.pid
.env
.env.*
!.env.example
!**/.env.example
```

### 12. Actualizar `README.md` (sección "GitHub Codespaces / QA")
Incluir: URL privada y cómo obtenerla, comandos de arranque/reinicio/parada, actualización desde Kilo, visibilidad privada, secretos, y estado de verificación (ver más abajo). También corregir la fila de "WebSocket connection" (ya es mismo origen) y la nota obsoleta sobre conectar al puerto 5000. Nota opcional: `frontend/package-lock.json` está gitignoreado → considerar commitearlo para builds reproducibles.

## Comandos a documentar y usar
- Arrancar todo: `bash .devcontainer/scripts/start.sh`
- Reiniciar servicios: `bash .devcontainer/scripts/restart.sh`
- Detener servicios: `bash .devcontainer/scripts/stop.sh`
- Actualizar cambios subidos desde Kilo (dentro del Codespace):
  `git pull --ff-only origin kilo/steep-velvet-t9n` y `bash .devcontainer/scripts/start.sh` (si cambió `requirements.txt`/`package.json`, re-ejecutar `bash .devcontainer/scripts/setup.sh`).
- Detener Codespace: UI (Codespaces → Stop) o `gh codespace stop -c <nombre>`.
- URL del frontend: `https://<nombre-codespace>-3000.app.github.dev` (`gh codespace ports -c <nombre>`).

## Paso manual (creación del Codespace) — obligatorio por credenciales
Con `gh` autenticado en la cuenta `gabowo001`:
```
gh codespace create \
  --repo gabowo001/roomroam \
  --branch kilo/steep-velvet-t9n \
  --machine basicLinux32gb \
  --idle-timeout 10m
```
Alternativa UI: Code → Codespaces → New with options → rama, región, máquina **2 cores**, idle 10 min. Luego, dentro del Codespace, forzar visibilidad si hace falta: `gh codespace ports visibility 3000:private -c "$CODESPACE_NAME"`. No cambiar ajustes de facturación.

## Verificación
Verificable en este sandbox:
1. `frontend`: `npm install` y `npm run build` (valida TypeScript + build de Vite).
2. Sintaxis: parsear `devcontainer.json` (JSON) y `docker-compose.yml` (YAML) — usar `node` o instalar/validar con python si queda disponible.
3. Backend/DB local (best-effort): instalar `python3 python3-venv postgresql` por apt, crear rol/BD, `pip install -r requirements.txt`, arrancar backend y ejercer `/api/test`, register, login, `/api/groups/*`, `/api/messages` y WS. Si apt/tiempo no lo permite, reportar como pendiente.
4. Requisito 5: ejecutar `gh codespace create ...` una vez y capturar el error 403 esperado; documentar como pendiente con el comando exacto.

Pendiente (requiere el Codespace real, que no podemos crear):
5. Build/arranque del contenedor compose, conexión a PostgreSQL en `db:5432`, y flujos end-to-end en navegador (registro, login, salas, favoritos, mensajes por WSS).
6. Protección de acceso: confirmar que en una ventana sin sesión de GitHub la URL privada no carga y que solo `gabowo001` accede.

## Riesgos / notas
- Si `InitializeCommand` no corre en el host del Codespace, compose usa el default `roomroam_dev` y `setup.sh` debe generar `backend/.env` con ese password (añadir fallback en `setup.sh`).
- Push del token: si `git push` falla por permisos, entregar el diff/patch al usuario y documentar el push manual.
- Backend single-process (salas WS en memoria) → no escalar a varios workers.
- Rebuild del contenedor borra el volumen `roomroam-pgdata` (datos) — stop/start NO lo borra. Documentarlo.
- No usar túneles públicos ni cambiar puertos a Public.

## Entregables
- Configuración `.devcontainer/` completa (compose `app`+`db`), cambios en `backend/app.py` y `frontend/vite.config.ts`, `.gitignore` y `README.md` actualizados, subidos a `kilo/steep-velvet-t9n`.
- Comandos de arranque/reinicio/parada/actualización/detención.
- URL privada (patrón + cómo obtenerla) y el paso manual exacto de creación del Codespace si las credenciales no lo permiten.
- Reporte de verificación: qué se verificó y qué quedó pendiente.
