# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SarahIA** is an AI-powered automated call system that confirms workforce shifts with workers. It uses ElevenLabs as the voice AI agent and Asterisk PBX for telephony.

## Development Commands

### Full stack (production-like)
```bash
docker compose up --build          # Build and start all services
docker compose up --build <service> # Rebuild a single service (e.g. backend-api)
docker compose logs -f <service>   # Follow logs for a service
```

### Backend (confirmation_agent_be) — local dev
```bash
cd confirmation_agent_be
source venv/Scripts/activate       # Windows/WSL
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7676 --reload          # Main API
uvicorn agent_api.api:app --host 0.0.0.0 --port 7575 --reload # Agent/Webhook API
celery -A tasks worker --loglevel=info                          # Worker
celery -A tasks beat --loglevel=info                           # Scheduler
```

### Frontend (confirmation_agent_fe) — local dev
```bash
cd confirmation_agent_fe
npm install
npm run dev      # Starts Next.js on port 7777
npm run build
npm run lint
```

### AMI Bridge (AMI) — local dev
```bash
cd AMI
npm install
node AMI.js
```

## Architecture

### Services and Ports

| Service | Port | Technology |
|---------|------|------------|
| AMI Bridge | 8282 | Node.js / Express |
| Backend API | 7676 | FastAPI (uvicorn) |
| Agent API | 7575 | FastAPI (uvicorn) |
| Frontend | 7777 | Next.js |
| Nginx gateway | 7373 (HTTP), 7001 (HTTPS) | nginx |
| Redis | 6380 (host) → 6379 (container) | Redis |

Nginx routing:
- `http://<host>:7373/SchedulerAgent/` → Frontend
- `http://<host>:7373/SchedulerAgent/API/` → Backend API
- `https://voice.moovin.me:7001/SarahIA/Agent/` → Agent API (ElevenLabs webhooks, HTTPS required)

### Call Flow

1. An external scheduler system POSTs to `POST /calls/add` with the worker's call context (name, shift details, phones).
2. **Backend API** (`main.py`) schedules a Celery task `disparar_llamada_ami` with an ETA.
3. At scheduled time, the Celery worker stores full context in Redis under `call_data:{call_id}` and calls the AMI Bridge's `/originate`.
4. **AMI Bridge** (`AMI.js`) sends an Asterisk `Originate` command that dials ElevenLabs' agent extension, which then calls the worker.
5. ElevenLabs fires the **pre-call webhook** (`POST /webhooks/elevenlabs-pre-call`) to fetch the call context from Redis and return dynamic variables to the agent.
6. The AI conducts the conversation. If it detects a problem (voicemail, no answer), it calls `POST /webhooks/call-issue-detected`.
7. After the call, ElevenLabs fires **post-call webhooks**: `post_call_transcription` (analysis) and `post_call_audio` (base64 audio). Both update Redis.
8. **Celery Beat** runs `sync_call_status` every 15 seconds, reading `call_status:{call_id}` from Redis to decide: complete, retry on next phone number, or fail.
9. Retry logic: tries `phone` → `alternative_phone` → `alternative_phone_2`, then marks final status.
10. `tarea_finalizar_y_enviar_reporte` waits for audio to arrive before sending the report via `send_call_report` in `utils.py`.

### Redis Key Schema

- `call_data:{call_id}` — Full JSON object: status, phone numbers, call_record (per-number results + ElevenLabs analysis), context, agent_instructions. TTL: 24h.
- `call_status:{call_id}` — Simple string: `DISPATCHED`, `COMPLETED`, `FAILED`, `BUSY`, `NOANSWER`, `RETRYING`. TTL: 24h.
- `temp_audio:{conversation_id}` — Base64 audio stored temporarily when audio arrives before transcription. TTL: 10 min.

### Persistent Storage

`db.json` (in `confirmation_agent_be/`) is the JSON file database for scheduled calls. It is volume-mounted into all backend containers so changes persist. `utils.py` provides `leer_db()` / `guardar_db()` / `agregar_llamada()` / `actualizar_llamada()` / `eliminar_llamada()` for all DB operations.

### Authentication

- **Backend API**: `Auth-Token` header compared against `NEXT_PUBLIC_AUTH_TOKEN` env var.
- **Agent API webhooks**: Pre-call uses `auth-token` header. Post-call uses HMAC-SHA256 signature verification with `ELEVENLABS_WEBHOOK_SIGNATURE`.
- **Frontend**: Login page accepts `ACCESS_KEY` env var, returns a JWT signed with `JWT_SECRET` stored in an `httpOnly` cookie (`session_token`). Middleware in `src/middleware.ts` protects all routes except `/Login`.

### Frontend Structure

The Next.js app uses the App Router with route groups:
- `(auth)/Login/` — login page (public)
- `(Home)/CallsStatusLogger/` — main dashboard (protected), polls every 15s
- `api/session/` — JWT session creation endpoint

`calls_services.js` has a hardcoded `IS_PROD = true` flag. In prod mode it calls the production URL directly; in dev mode it appends `/dev` to use the dev endpoints (which skip Celery scheduling and just write to `db.json`).

### Dev vs Production Endpoints

The backend exposes both production and development variants:
- `POST /calls/add` — schedules via Celery (prod)
- `POST /calls/add/dev` — writes directly to db.json (dev)
- Same pattern for update and delete.

## Required Environment Variables

All services read from a single `.env` file at the repo root:

```
REDIS_URL=redis://:password@127.0.0.1:6380/0
REDIS_PASSWORD=
NEXT_PUBLIC_AUTH_TOKEN=       # Shared API token FE ↔ BE
JWT_SECRET=                   # FE session JWT secret
ACCESS_KEY=                   # FE login password
AMI_URL=                      # URL of AMI bridge /originate endpoint
AMI_CONTROL_TOKEN=            # Token for AMI bridge auth
AMI_EXTENSION=                # Asterisk extension for ElevenLabs agent
AMI_HOST=127.0.0.1
AMI_PORT=5038
AMI_USER=
AMI_PASS=
AMI_TRANSFER_CONTEXT=         # Asterisk dialplan context for transfers
ELEVENLABS_WEBHOOK_SIGNATURE= # HMAC secret for post-call webhook
```
