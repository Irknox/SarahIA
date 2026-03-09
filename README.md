# SarahIA — Sistema de Confirmacion de Turnos por IA

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5+-37814A?style=flat-square&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-gateway-009639?style=flat-square&logo=nginx&logoColor=white)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Voice_AI-000000?style=flat-square&logoColor=white)
![Asterisk](https://img.shields.io/badge/Asterisk-PJSIP-F47C20?style=flat-square&logoColor=white)

SarahIA es un sistema de llamadas salientes automaticas que confirma turnos laborales con trabajadores usando un agente de voz basado en ElevenLabs y telefonia Asterisk (PJSIP).

---

## Arquitectura General

```
Scheduler Externo
      |
      | POST /calls/add
      v
+--------------+     Celery ETA      +------------------+
| Backend API  | ------------------> |  Celery Worker   |
|  (FastAPI)   |                     +--------+---------+
|  :7676       |                              | POST /originate
+--------------+                              v
                                     +------------------+
                                     |   AMI Bridge     |
                                     |   (Node.js)      |
                                     |   :8282          |
                                     +--------+---------+
                                              | Asterisk AMI Action: Originate
                                              v
                                     +------------------+
                                     |   Asterisk PBX   |
                                     |   Dialplan 7777  |
                                     +--------+---------+
                                              |
                                     Dial al humano (60s)
                                              |
                              +---------------+---------------+
                              |                               |
                         CONTESTA                     NO CONTESTA / BUSY
                              |                               |
                   Conecta con ElevenLabs            Redis: NOANSWER/BUSY
                   Redis: IN_PROGRESS                Celery Beat: reintento
                              |
                              v
                    +------------------+
                    |  ElevenLabs SIP  |
                    |  Agente "Sarah"  |
                    +--------+---------+
                             | Webhooks HTTPS
                             v
                    +------------------+
                    |   Agent API      |
                    |   (FastAPI)      |
                    |   :7575          |
                    +--------+---------+
                             | actualiza Redis
                             v
                    +------------------+
                    |  Celery Beat     |  (cada 15s)
                    |  sync_call_status|
                    +--------+---------+
                             |
                    +--------+--------+
                    v                 v
               COMPLETED          FAILED / RETRY
            Reporte final      Reporte parcial +
                               siguiente numero
```

---

## Flujo Detallado de una Llamada

### 1. Agendamiento

El sistema externo (SchedulerAgent) envia un `POST /calls/add` con el contexto completo del trabajador: nombre, fecha de turno, centro de trabajo, telefonos principal y alternativos, instrucciones para el agente, etc.

El Backend API:
- Parsea la fecha/hora con zona horaria `Europe/Madrid`
- Encola la tarea `disparar_llamada_ami` en Celery con ETA a la hora programada

---

### 2. Disparo (Celery Worker)

Al llegar la ETA, el worker ejecuta `disparar_llamada_ami`:
1. Guarda el contexto completo en Redis bajo `call_data:{call_id}` (TTL 24h)
2. Marca `call_status:{call_id}` = `DISPATCHED`
3. Llama al AMI Bridge: `POST /originate`

El AMI Bridge envia a Asterisk un comando `Originate` con:
- `Channel`: `Local/7777@from-internal-custom` (la extension 7777 ejecuta el flujo)
- `Context`: `bridge-outbound` (canal de soporte para el Local channel)
- Variables: `DESTINO_HUMANO` (numero del trabajador), `X_CALL_ID` (ID interno)

---

### 3. Dialplan Asterisk — Extension 7777

El flujo telefonico esta definido en `pjsip.extensions_custom_simplified.conf`:

```
Originate crea Local channel con dos patas:
  ;2 -> entra a from-internal-custom, extension 7777
  ;1 -> entra a bridge-outbound (Wait, canal de soporte)

Extension 7777
|
+- Redis: call_status:{ID} = DISPATCHED
+- Set(IS_CALLER=1) en el canal ;2
|
+- Dial(PJSIP/{NUM_HUMANO}@ext-remote, timeout=60s)
|   con G(from-internal-custom^7777^10)
|
+-- Si NO contesta / BUSY / Error de red:
|     handler-finalizar -> Redis: NOANSWER / BUSY / FAILED
|
+-- Si CONTESTA -> G() redirige ambos canales a priority 10:
      |
      +- Canal ;2 (IS_CALLER=1) -> Hangup limpio
      |
      +- Canal ext-remote (humano):
          +- Redis: call_status:{ID} = IN_PROGRESS
          +- Dial(ElevenLabs SIP endpoint)
          |    Headers SIP: X-Call-ID, X-Caller-ID
          +- Si ElevenLabs no contesto -> Redis: FAILED
          +- Si ElevenLabs contesto -> Redis queda IN_PROGRESS
               (el webhook de ElevenLabs define el estado final)
```

#### Separacion de canales con IS_CALLER
Cuando el humano contesta, `G()` redirige **ambos** canales (el caller `;2` y el called `ext-remote`) a la misma prioridad. Para evitar que ambos ejecuten el Dial a ElevenLabs, se usa una variable `IS_CALLER` (sin prefijo de herencia) que solo existe en `;2`. Al llegar a priority 10, `;2` detecta la variable y hace Hangup; `ext-remote` (que no la tiene) continua y conecta con Sarah.

#### bridge-outbound
El contexto `bridge-outbound` es el destino de la pata `;1` del Local channel. Solo hace `Wait(600)` para mantener vivo el canal. Cuando `;2` cuelga, `;1` muere automaticamente.

---

### 4. Webhooks de ElevenLabs -> Agent API (:7575)

El Agent API esta expuesto via HTTPS a traves de Nginx.

#### Pre-call: `POST /webhooks/elevenlabs-pre-call`
Autenticacion: header `auth-token`

ElevenLabs lo llama antes de que el agente hable. El sistema busca el contexto en Redis usando los headers SIP (`X-Call-ID`) y responde con las variables dinamicas del turno (nombre del trabajador, fecha, horario, centro, instrucciones del agente). El agente arranca con:
> *"Hola mi nombre es Sarah de Eurofirms, estoy hablando con {nombre}?"*

#### Post-call transcription: `POST /webhooks/elevenlabs-post-call`
Autenticacion: firma HMAC-SHA256 (header `elevenlabs-signature` con formato `t=<timestamp>,v0=<hash>`)

Recibe el analisis completo de la conversacion:
- `call_successful`: `success` / `failure`
- `transcript_summary`
- `evaluation_criteria_results_list`
- `data_collection_results_list`

Si `success` -> Redis: `call_status` = `COMPLETED`
Si `failure` -> Redis: `call_status` = `FAILED`

Si el audio (base64) ya habia llegado antes que la transcripcion, lo recupera de `temp_audio:{conversation_id}` y lo adjunta al analisis.

#### Post-call audio: `POST /webhooks/elevenlabs-post-call` (evento `post_call_audio`)
Recibe el audio completo de la llamada en base64. Busca en Redis el `call_data` que tenga el `conversation_id` correspondiente y adjunta el audio al analisis de ElevenLabs. Si el audio llega antes que la transcripcion, se guarda temporalmente en `temp_audio:{conversation_id}` (TTL 10 min).

#### Call issue detected: `POST /webhooks/call-issue-detected`
Autenticacion: header `auth-token`

El agente llama a este endpoint cuando detecta buzon de voz, silencio prolongado, o cualquier condicion que impide la confirmacion. Marca el numero como `FAILED` con la razon detectada por la IA.

#### Tools: `POST /tools`
Autenticacion: header `auth-token`

Endpoint que ElevenLabs llama para ejecutar herramientas durante la conversacion:
- `applyDecision` — registra la decision del trabajador (acepta/rechaza turno) en Redis bajo `call_data:{call_id}.context.confirmation`

---

### 5. Orquestador — Celery Beat (cada 15 segundos)

`sync_call_status` lee todos los `call_status:*` de Redis y decide:

| Estado Redis | Condicion | Accion |
|---|---|---|
| `COMPLETED` | — | Finalizar y enviar reporte final |
| `FAILED` / `BUSY` / `NOANSWER` | — | `preparar_reintento_o_fallo` |
| `DISPATCHED` / `IN_PROGRESS` | > 5 min sin cambio | Forzar cierre con estado actual |

#### Logica de reintentos
Se intenta en orden: `phone` -> `alternative_phone` -> `alternative_phone_2`

Si hay siguiente numero disponible:
- El numero actual se marca como `FAILED` con la razon del fallo
- Se envia un **reporte parcial** con el resultado de ese numero
- Se encola `disparar_llamada_ami` con `countdown=300s` (5 min) para el siguiente numero

Si la herramienta `applyDecision` fue usada durante la llamada (el trabajador respondio), no se reintenta aunque el estado sea `FAILED`.

Si no hay mas numeros: se envia el **reporte final** con estado `FAILED`.

---

### 6. Reportes

El sistema envia dos tipos de reportes al webhook del scheduler externo:

#### Reporte parcial
Se envia cuando un numero falla y hay numeros alternativos pendientes. Contiene:
- `call_id`
- `type`: `"partial"`
- `phone_record`: resultado del numero que fallo (estado, razon, analisis de ElevenLabs, audio si hubo conversacion)

#### Reporte final
Se envia cuando el ciclo de llamada termina (exito o todos los numeros agotados). La tarea `tarea_finalizar_y_enviar_reporte` espera hasta 5 minutos (con reintentos cada 30s) a que el audio base64 este disponible antes de enviar. Contiene:
- `call_id`
- `type`: `"final"`
- `status`: `COMPLETED` o `FAILED`
- `call_context`: contexto completo del turno
- `call_record`: resultado del ultimo numero intentado (con analisis y audio)

---

## Endpoints

### Backend API
Auth: header `Auth-Token`

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/calls` | Lista todos los registros en db.json |
| POST | `/calls/add` | Agenda llamada via Celery (produccion) |
| PUT | `/calls/update/{id}` | Actualiza y re-agenda llamada |
| DELETE | `/calls/delete/{id}` | Elimina registro y revoca tarea Celery |
| POST | `/calls/add/dev` | Agrega registro sin Celery (desarrollo) |
| PUT | `/calls/update/dev/{id}` | Actualiza sin re-agendar (desarrollo) |
| DELETE | `/calls/delete/dev/{id}` | Elimina sin revocar tarea (desarrollo) |

### Agent API

| Metodo | Ruta | Auth | Llamado por |
|--------|------|------|-------------|
| POST | `/webhooks/elevenlabs-pre-call` | `auth-token` header | ElevenLabs (antes de llamar) |
| POST | `/webhooks/elevenlabs-post-call` | HMAC-SHA256 signature | ElevenLabs (post llamada) |
| POST | `/webhooks/call-issue-detected` | `auth-token` header | ElevenLabs (deteccion de problemas) |
| POST | `/tools` | `auth-token` header | ElevenLabs (tool call) |

### AMI Bridge — interno, no expuesto publicamente

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/originate` | `x-ari-control-token` header | Dispara llamada en Asterisk |

---

## Redis — Esquema de Claves

| Clave | Contenido | TTL |
|-------|-----------|-----|
| `call_data:{call_id}` | JSON completo: status, telefonos, call_record por numero, contexto, instrucciones | 24h |
| `call_status:{call_id}` | String: `DISPATCHED` / `IN_PROGRESS` / `COMPLETED` / `FAILED` / `BUSY` / `NOANSWER` / `RETRYING` | 24h |
| `temp_audio:{conversation_id}` | Audio base64 temporal (llega antes que la transcripcion) | 10 min |

`DISPATCHED` e `IN_PROGRESS` los escribe **Asterisk** via `redis-cli` desde el dialplan. `COMPLETED` y `FAILED` los escribe el **webhook post_call_transcription** de ElevenLabs. `BUSY`, `NOANSWER` y `FAILED` (por error de red) los escribe **handler-finalizar** en el dialplan cuando el humano no contesta. Ambas claves se eliminan de Redis al enviar el reporte final.

---

## Variables de Entorno

Se configuran en un archivo `.env` en la raiz del proyecto (no versionado):

```env
# Redis
REDIS_URL=redis://:<REDIS_PASSWORD>@127.0.0.1:6380/0
REDIS_PASSWORD=<redis_password>

# Token compartido entre el scheduler externo y las APIs
NEXT_PUBLIC_AUTH_TOKEN=<shared_api_token>

# Frontend
JWT_SECRET=<jwt_secret>
ACCESS_KEY=<frontend_access_key>

# AMI Bridge (comunicacion interna con Asterisk)
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

El archivo `AMI/pjsip.extensions_custom_simplified.conf` contiene el dialplan utilizado. Solo la extension 7777 y sus contextos de soporte son relevantes para SarahIA:

| Extension / Contexto | Descripcion |
|-----------|-------------|
| `bridge-outbound` | Canal de soporte para el Local channel. Solo hace `Wait()` para mantener viva la pata `;1` |
| `7777` | Flujo principal: dial al trabajador, separacion de canales con `IS_CALLER`, conexion a ElevenLabs |
| `handler-finalizar` | Mapea `DIALSTATUS` al estado correspondiente en Redis (`BUSY` / `NOANSWER` / `FAILED`) |
| `add-elevenlabs-headers` | Inyecta `X-Call-ID` y `X-Caller-ID` en los headers SIP del INVITE hacia ElevenLabs |

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
