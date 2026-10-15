# RoomRoam

RoomRoam is a real-time group chat prototype where you can join a random room, exchange messages, save favorite rooms, and return to them later.

This repository contains both the React frontend and the Python backend.

## Features

- Username/password registration and cookie-based authentication.
- Random room discovery and switching between rooms.
- Favorite rooms with a sidebar for returning to saved conversations.
- Persistent users, rooms, favorites, and message history in PostgreSQL.
- Real-time message delivery over WebSockets.
- Connection status indicator and responsive chat interface.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, TypeScript, Vite 4, Axios |
| Backend | Python, Quart, Quart-Auth, Quart-CORS, Hypercorn |
| Persistence | PostgreSQL, SQLAlchemy, psycopg2 |
| Password hashing | bcrypt |

## Local setup

### Prerequisites

- Git.
- Python 3 with `pip` and `venv`.
- Node.js and npm.
- A running PostgreSQL server and a database user allowed to create tables in the selected database.

The commands below use Bash on Linux or macOS.

### 1. Clone the repository

```bash
git clone https://github.com/gabowo001/roomroam.git
cd roomroam
```

### 2. Prepare PostgreSQL

Use an existing development database, or create a dedicated user and database. For example, on Linux with a local PostgreSQL installation:

```bash
sudo -u postgres createuser --pwprompt roomroam
sudo -u postgres createdb --owner=roomroam roomroam
```

Keep the password you enter for the backend configuration below. The backend creates its tables automatically on startup; you do not need to run the database reset script for first-time setup.

### 3. Start the backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with your database credentials and a generated secret key:

```dotenv
DATABASE_URL=postgresql://roomroam:your_password@localhost:5432/roomroam
SECRET_KEY=replace-with-a-generated-secret
PORT=5000
```

You can generate a secret with:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

If the database password contains URL-reserved characters, percent-encode them in `DATABASE_URL`.

Start the API and WebSocket server:

```bash
python app.py
```

The backend listens on port **5000** by default. Check that it is running:

```bash
curl http://localhost:5000/api/test
```

Expected response:

```json
{"success": true, "message": "Server is working!"}
```

### 4. Start the frontend

Open a second terminal and run these commands from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 5. Try the chat

1. Create an account using **Sign Up**. Registration currently creates the account without signing it in, so reload the page afterward and use **Sign In**.
2. Signing in assigns you to a random room. The backend creates an initial set of rooms if none exist.
3. Send a message, save the room as a favorite, or leave to join another random room.
4. Open the sidebar to return to a saved room or remove it from favorites.

To try real-time delivery with two users, use separate browser profiles or a private window, and join the same room.

## Configuration and networking

| Setting | Where it is configured | Current behavior |
| --- | --- | --- |
| Database connection | `backend/.env`: `DATABASE_URL` | SQLAlchemy uses a PostgreSQL connection URL. |
| Session signing key | `backend/.env`: `SECRET_KEY` | Signs authentication cookies. |
| Backend port | `backend/.env`: `PORT` | Defaults to `5000`; keep this value for the frontend's current defaults. |
| Frontend port | `frontend/vite.config.ts` | Vite serves the UI on `3000`. |
| HTTP API | `frontend/vite.config.ts` | Browser requests to `/api` are proxied to `http://127.0.0.1:5000`. |
| WebSocket connection | `frontend/src/services/websocketManager.ts` | Connects directly to the browser's current hostname on port `5000`, at `/ws`. |

The frontend currently does **not** read `VITE_API_URL` or `VITE_WS_URL` from `frontend/.env.example`. Copying that file or changing those variables does not change the connection targets.

Although Vite also defines a `/ws` proxy, the current WebSocket client connects directly to the backend. If you change the backend port, update both the Vite proxy targets and the WebSocket manager. For access from another device, that device must be able to reach ports `3000` and `5000` on the development machine.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/app.py` | Active Quart application, authentication, room/message APIs, and WebSocket handling. |
| `backend/models.py` | SQLAlchemy models and database initialization. |
| `backend/requirements.txt` | Python dependencies. |
| `backend/.env.example` | Example backend environment configuration. |
| `backend/reset_db.py` | Drops and recreates the application tables, deleting their data. |
| `backend/test_db.py`, `backend/test_register.py` | Manual database diagnostics that modify test-user data. |
| `frontend/src/pages/Chat.tsx` | Chat state and room actions. |
| `frontend/src/components/` | Login, header, sidebar, message list, and input components. |
| `frontend/src/services/websocketManager.ts` | WebSocket connection and reconnection handling. |
| `frontend/vite.config.ts` | Development server and proxy configuration. |

## API overview

Except for the health check, registration, and login, the routes below require an authenticated session.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/test` | Check that the server is running. |
| POST | `/api/register` | Create an account with `username` and `password`. |
| POST | `/api/login` | Sign in with `username` and `password`. |
| POST | `/api/logout` | Sign out. |
| GET | `/api/groups/random` | Assign the user to a random room. |
| POST | `/api/groups/join/<group_id>` | Join a specific room. |
| POST | `/api/groups/leave` | Leave the room; `{"join_new": true}` selects another random room. |
| POST | `/api/groups/like` | Save the current room as a favorite. |
| GET | `/api/groups/saved` | List the user's favorite rooms. |
| POST | `/api/groups/unsave/<group_id>` | Remove a favorite. |
| GET | `/api/messages` | Retrieve message history; defaults to the current room. |
| POST | `/api/messages` | Send a message using `{"text": "..."}`. |
| WebSocket | `/ws` | Receive message history and live messages for the current room. |

Messages are submitted through the HTTP API and delivered to connected room clients through WebSockets.

## Frontend commands

Run these inside `frontend/`:

```bash
npm run dev      # Start Vite's development server
npm run build    # Type-check and build into dist/
npm run preview  # Preview the built frontend
npm test         # Start Vitest
```

The repository currently contains no frontend test files. The Python files named `test_*.py` are manual database scripts rather than an isolated automated test suite; they write to the configured database and do not load `.env` themselves.

`npm run preview` serves the frontend build only. A deployed frontend needs routing for `/api` and an accessible WebSocket backend; the local development setup above uses Vite's proxy.

## Development status

The current configuration targets local development: authentication cookies allow HTTP, CORS allows all origins, and request logging includes headers and cookies. WebSocket room connections are kept in process memory, so live broadcasts currently assume a single backend process.
