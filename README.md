# SarahIA — Sistema de Confirmación de Turnos por IA

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5+-37814A?style=flat-square&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-gateway-009639?style=flat-square&logo=nginx&logoColor=white)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Voice_AI-000000?style=flat-square&logoColor=white)
![Asterisk](https://img.shields.io/badge/Asterisk-PJSIP-F47C20?style=flat-square&logoColor=white)

SarahIA es un sistema de llamadas salientes automáticas que confirma turnos laborales con trabajadores usando un agente de voz basado en ElevenLabs y telefonía Asterisk (PJSIP).

---

## Arquitectura General

```
Scheduler Externo
      │
      │ POST /calls/add
      ▼
┌─────────────┐     Celery ETA      ┌──────────────────┐
│ Backend API │ ──────────────────► │  Celery Worker   │
│  (FastAPI)  │                     └────────┬─────────┘
│  :7676      │                              │ POST /originate
└─────────────┘                              ▼
                                    ┌──────────────────┐
                                    │   AMI Bridge     │
                                    │   (Node.js)      │
                                    │   :8282          │
                                    └────────┬─────────┘
                                             │ Asterisk AMI Action: Originate
                                             ▼
                                    ┌──────────────────┐
                                    │   Asterisk PBX   │
                                    │   Dialplan 7777  │
                                    └────────┬─────────┘
                              ┌──────────────┴──────────────┐
                              │ Dial al humano + AMD         │
                              ▼                             ▼
                         ES HUMANO                   ES CONTESTADORA
                              │                             │
                              │                    Redis: NOANSWER
                              │                    Celery Beat: reintento
                              ▼
                    ┌──────────────────┐
                    │  ElevenLabs SIP  │
                    │  Agente "Sarah"  │
                    └────────┬─────────┘
                             │ Webhooks HTTPS
                             ▼
                    ┌──────────────────┐
                    │   Agent API      │
                    │   (FastAPI)      │
                    │   :7575          │
                    └────────┬─────────┘
                             │ actualiza Redis
                             ▼
                    ┌──────────────────┐
                    │  Celery Beat     │  (cada 15s)
                    │  sync_call_status│
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
               COMPLETED          FAILED / RETRY
               Reporte final      Siguiente número
```

---

## Flujo Detallado de una Llamada

### 1. Agendamiento

El sistema externo (SchedulerAgent) envía un `POST /calls/add` con el contexto completo del trabajador: nombre, fecha de turno, centro de trabajo, teléfonos principal y alternativos, instrucciones para el agente, etc.

El Backend API:
- Parsea la fecha/hora con zona horaria `Europe/Madrid`
- Encola la tarea `disparar_llamada_ami` en Celery con ETA a la hora programada

---

### 2. Disparo (Celery Worker)

Al llegar la ETA, el worker ejecuta `disparar_llamada_ami`:
1. Guarda el contexto completo en Redis bajo `call_data:{call_id}` (TTL 24h)
2. Marca `call_status:{call_id}` = `DISPATCHED`
3. Llama al AMI Bridge: `POST http://localhost:8282/originate`

El AMI Bridge envía a Asterisk un comando `Originate` apuntando a la extensión 7777 del contexto `from-internal-custom`, con las variables:
- `DESTINO_HUMANO` — número del trabajador
- `X_CALL_ID` — ID interno de la llamada

---

### 3. Dialplan Asterisk — Extensión 7777

Este es el corazón del flujo telefónico (`pjsip.extensions_custom.conf`):

```
Extensión 7777
│
├─ Marca Redis: call_status:{ID} = DISPATCHED
│
├─ Dial(PJSIP/{NUM_HUMANO}@ext-remote, timeout=60s)
│   └─ Subrutina: sub-validar-voz (se ejecuta en el canal del humano)
│       ├─ AMD() — Answering Machine Detection
│       ├─ HUMAN  → Redis: IN_PROGRESS | ES_HUMANO=1
│       └─ MACHINE → Redis: NOANSWER   | ES_HUMANO=0
│
├─ Prioridad 10 (maestro): evalúa ES_HUMANO
│   ├─ ES_HUMANO=1 → conectar_eleven
│   │   └─ Dial(ElevenLabs SIP endpoint)
│   │       Headers SIP: X-Call-ID, X-Caller-ID
│   │
│   └─ ES_HUMANO=0 → handler-finalizar
│       └─ Mapea DIALSTATUS → COMPLETED/BUSY/NOANSWER/FAILED
│          Actualiza Redis
```

#### Detección AMD
Asterisk ejecuta `AMD()` en el canal del humano mientras la llamada está activa:
- `HUMAN` → el canal sigue adelante para conectar con ElevenLabs
- `MACHINE` / contestadora → se marca `NOANSWER` en Redis y el canal se cuelga. Celery Beat recogerá esto y reintentará con el número alternativo.

#### Conexión a ElevenLabs
Al confirmar que hay un humano, Asterisk marca el canal con `X-Call-ID` y `X-Caller-ID` en los headers SIP del INVITE hacia ElevenLabs, para que el agente pueda correlacionar la llamada con el contexto guardado en Redis.

---

### 4. Webhooks de ElevenLabs → Agent API (:7575)

El Agent API está expuesto en HTTPS via Nginx en `https://<AGENT_DOMAIN>/SarahIA/Agent/`.

#### Pre-call: `POST /webhooks/elevenlabs-pre-call`
Autenticación: header `auth-token: <AUTH_TOKEN>`

ElevenLabs lo llama antes de que el agente hable. El sistema responde con las variables dinámicas del turno (nombre del trabajador, fecha, horario, centro, instrucciones del agente). El agente arranca con:
> *"Hola mi nombre es Sarah de Eurofirms, estoy hablando con {nombre}?"*

#### Post-call transcription: `POST /webhooks/elevenlabs-post-call`
Autenticación: firma HMAC-SHA256 (header `elevenlabs-signature` con formato `t=<timestamp>,v0=<hash>`)

Recibe el análisis completo de la conversación:
- `call_successful`: `success` / `failure`
- `transcript_summary`
- `evaluation_criteria_results_list`
- `data_collection_results_list`

Si `success` → Redis: `call_status` = `COMPLETED`
Si `failure` → Redis: `call_status` = `FAILED`

El agente de ElevenLabs también tiene un **fallback de buzón de voz**: si durante la conversación detecta que habla con una contestadora (aunque AMD no lo haya filtrado), llama a `/webhooks/call-issue-detected` para reportarlo.

#### Post-call audio: `POST /webhooks/elevenlabs-post-call` (evento `post_call_audio`)
Recibe el audio completo de la llamada en base64. Si el audio llega antes que la transcripción, se guarda en `temp_audio:{conversation_id}` (TTL 10 min) hasta que llegue la transcripción.

#### Call issue detected: `POST /webhooks/call-issue-detected`
Autenticación: header `auth-token: <AUTH_TOKEN>`

El agente llama a este endpoint cuando detecta buzón de voz o cualquier condición que impide la confirmación. Marca el número como `FAILED` con la razón detectada por la IA.

#### Tools: `POST /tools`
Autenticación: header `auth-token: <AUTH_TOKEN>`

Endpoint que ElevenLabs llama para ejecutar herramientas durante la conversación:
- `applyDecision` — registra la decisión del trabajador en Redis bajo `call_data:{call_id}.context.confirmation`

---

### 5. Orquestador — Celery Beat (cada 15 segundos)

`sync_call_status` lee todos los `call_status:*` de Redis y decide:

| Estado Redis | Condición | Acción |
|---|---|---|
| `COMPLETED` | — | Finalizar y enviar reporte |
| `FAILED` / `BUSY` / `NOANSWER` | — | `preparar_reintento_o_fallo` |
| Cualquiera | > 5 min sin cambio | Forzar cierre con estado actual |

#### Lógica de reintentos
Se intenta en orden: `phone` → `alternative_phone` → `alternative_phone_2`

Si hay siguiente número disponible:
- El número actual se marca como `FAILED`
- Se encola `disparar_llamada_ami` con `countdown=300s` (5 min) para el siguiente número

Si no hay más números: `finalizar_y_reportar` con estado `FAILED`.

---

### 6. Reporte Final

`tarea_finalizar_y_enviar_reporte` espera a que el audio base64 esté disponible (si hubo conversación) antes de enviar el reporte. El reporte incluye:
- Estado final de la llamada
- Registro por número intentado (resultado + análisis de ElevenLabs)
- Contexto del turno
- Audio de la conversación

---

## Endpoints

### Backend API — `http://<SERVER_IP>:<GATEWAY_PORT>/SchedulerAgent/API`
Auth: header `Auth-Token: <AUTH_TOKEN>`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/calls` | Lista todos los registros en db.json |
| POST | `/calls/add` | Agenda llamada vía Celery (producción) |
| PUT | `/calls/update/{id}` | Actualiza y re-agenda llamada |
| DELETE | `/calls/delete/{id}` | Elimina registro y revoca tarea Celery |
| POST | `/calls/add/dev` | Agrega registro sin Celery (desarrollo) |
| PUT | `/calls/update/dev/{id}` | Actualiza sin re-agendar (desarrollo) |
| DELETE | `/calls/delete/dev/{id}` | Elimina sin revocar tarea (desarrollo) |

### Agent API — `https://<AGENT_DOMAIN>/SarahIA/Agent`

| Método | Ruta | Auth | Llamado por |
|--------|------|------|-------------|
| POST | `/webhooks/elevenlabs-pre-call` | `auth-token` header | ElevenLabs (antes de llamar) |
| POST | `/webhooks/elevenlabs-post-call` | HMAC-SHA256 signature | ElevenLabs (post llamada) |
| POST | `/webhooks/call-issue-detected` | `auth-token` header | ElevenLabs (fallback buzón) |
| POST | `/tools` | `auth-token` header | ElevenLabs (tool call) |

### AMI Bridge — interno, no expuesto públicamente

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/originate` | `x-ari-control-token` header | Dispara llamada en Asterisk |

---

## Redis — Esquema de Claves

| Clave | Contenido | TTL |
|-------|-----------|-----|
| `call_data:{call_id}` | JSON completo: status, teléfonos, call_record por número, contexto, instrucciones | 24h |
| `call_status:{call_id}` | String: `DISPATCHED` / `IN_PROGRESS` / `COMPLETED` / `FAILED` / `BUSY` / `NOANSWER` / `RETRYING` | 24h |
| `temp_audio:{conversation_id}` | Audio base64 temporal (llega antes que la transcripción) | 10 min |

Los estados `IN_PROGRESS` y `DISPATCHED` los escribe directamente **Asterisk** via `redis-cli` desde el dialplan. El resto los escriben los webhooks de ElevenLabs y Celery.

---

## Variables de Entorno

Se configuran en un archivo `.env` en la raíz del proyecto (no versionado):

```env
# Redis
REDIS_URL=redis://:<REDIS_PASSWORD>@127.0.0.1:6380/0
REDIS_PASSWORD=<redis_password>

# Token compartido entre el scheduler externo y las APIs
NEXT_PUBLIC_AUTH_TOKEN=<shared_api_token>

# Frontend (prototipo)
JWT_SECRET=<jwt_secret>
ACCESS_KEY=<frontend_access_key>

# AMI Bridge (comunicación interna con Asterisk)
AMI_URL=<ami_bridge_url>
AMI_CONTROL_TOKEN=<ami_control_token>
AMI_EXTENSION=<elevenlabs_agent_extension>

# Asterisk
AMI_HOST=<asterisk_host>
AMI_PORT=<asterisk_ami_port>
AMI_USER=<asterisk_ami_user>
AMI_PASS=<asterisk_ami_password>
AMI_TRANSFER_CONTEXT=<asterisk_dialplan_context>

# ElevenLabs
ELEVENLABS_WEBHOOK_SIGNATURE=<elevenlabs_hmac_secret>
```

---

## Dialplan Asterisk

El archivo `AMI/pjsip.extensions_custom.conf.example` contiene un ejemplo del dialplan. Cópialo a `/etc/asterisk/pjsip.extensions_custom.conf` en tu instalación de Asterisk, rellena los `<PLACEHOLDER>` con los valores de tu entorno y añádelo a la configuración de Asterisk junto a los endpoints PJSIP necesarios.

El archivo real (`pjsip.extensions_custom.conf`) no se versiona en Git por contener credenciales.

| Extensión / Contexto | Descripción |
|-----------|-------------|
| `bridge-outbound` | Punto de entrada desde el AMI Bridge (`AMI_TRANSFER_CONTEXT`) |
| `7777` | Flujo principal: dial al trabajador + AMD + conexión a ElevenLabs |
| `sub-validar-voz` | Subrutina AMD: detecta humano vs contestadora, actualiza Redis |
| `handler-finalizar` | Mapea `DIALSTATUS` al estado final en Redis |
| `add-elevenlabs-headers` | Inyecta `X-Call-ID` y `X-Caller-ID` en los headers SIP del INVITE |

---

## Despliegue

```bash
# Configurar variables de entorno
cp .env.example .env  # editar con los valores del entorno

# Construir e iniciar todos los servicios
docker compose up --build -d

# Ver logs
docker compose logs -f celery-worker
docker compose logs -f backend-api
```
