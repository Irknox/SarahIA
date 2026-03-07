# Guia de Integracion - Webhook Call Report

## Endpoint

```
POST https://<HOST>/api/call-requests/webhook/call-report
```

## Autenticacion

Enviar el token en el header `Auth-Token`:

```
Auth-Token: 435kjo3h4p6h34p56hbñlkn345h6IUGOUBJ
```

## Tipos de reporte

Se aceptan dos tipos de reporte en el mismo endpoint. El campo `type` determina cual es.

---

### 1. Reporte Parcial (`type: "partial"`)

Enviar cada vez que un numero falla (Asterisk o ElevenLabs). Solo incluye la info del intento fallido.

```json
{
  "call_id": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
  "type": "partial",
  "phone_record": {
    "number": "+34600000001",
    "status": "FAILED",
    "failed_reason": "AST_ISSUE",
    "elevenlabs_analysis": {
      "was_success": "failure",
      "termination_reason": "webhook_detected_voicemail",
      "summary": "La llamada fue atendida por un contestador automatico.",
      "evaluation_criteria": [
        {
          "criteria_id": "call_evaluation",
          "result": "failure",
          "rationale": "El agente no pudo completar la conversacion..."
        }
      ],
      "data_collection": [
        {
          "data_collection_id": "something_happened",
          "value": null,
          "rationale": "No se recopilo informacion relevante."
        }
      ],
      "dynamic_vars": {
        "system__call_sid": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
        "system__conversation_id": "conv_abc123",
        "system__call_duration_secs": 12,
        "system__caller_id": "+34600000001",
        "system__called_number": "3232",
        "system__agent_id": "agent_xyz",
        "system__time_utc": "2026-03-02T23:38:04.880372+00:00",
        "system__timezone": "Europe/Madrid"
      },
      "conversation_id": "conv_abc123",
      "base64_audio": "<string base64 MP3 o null>"
    }
  }
}
```

#### Campos del reporte parcial

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `call_id` | UUID | Si | ID de la llamada. Corresponde al `id` enviado en `/calls/add` |
| `type` | string | Si | Siempre `"partial"` |
| `phone_record` | object | Si | Registro del numero que fallo |

#### Campos de `phone_record`

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `number` | string | Si | Numero marcado (ej: `"+34600000001"`) |
| `status` | string | Si | Estado: `"FAILED"`, `"BUSY"`, `"NOANSWER"`, `"AST_FAILED"`, `"COMPLETED"` |
| `failed_reason` | string/null | Si | Motivo del fallo. `null` si no se determino |
| `elevenlabs_analysis` | object/null | No | Presente solo si la llamada llego a ElevenLabs |

#### Campos de `elevenlabs_analysis`

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `was_success` | string | Si | `"success"` o `"failure"` |
| `termination_reason` | string | No | Motivo tecnico de terminacion |
| `summary` | string/null | No | Resumen de la conversacion (texto libre) |
| `evaluation_criteria` | array | No | Criterios de evaluacion |
| `data_collection` | array | No | Datos recopilados |
| `dynamic_vars` | object | No | Variables del sistema ElevenLabs |
| `conversation_id` | string | No | ID de conversacion en ElevenLabs |
| `base64_audio` | string/null | No | Audio MP3 completo en base64. `null` si no disponible |

---

### 2. Reporte Final (`type: "final"`)

Enviar una sola vez al terminar el ciclo completo (llamada exitosa o todos los numeros agotados).
Incluye el contexto del turno pero SOLO el registro del ultimo numero intentado.

```json
{
  "call_id": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
  "type": "final",
  "status": "COMPLETED",
  "call_context": {
    "worker_first_name": "Elena",
    "worker_name": "Elena Garcia Lopez",
    "position": "Camarera",
    "work_center": "Hotel Miramar",
    "address": "Calle Gran Via 45, Madrid",
    "shift_date": "2026-03-06",
    "shift_start_time": "08:00",
    "shift_end_time": "16:00",
    "instructions": "Presentarse en recepcion",
    "hourly_rate": "12.50",
    "confirmation": "Turno confirmado"
  },
  "call_record": {
    "alternative_phone": {
      "number": "+34600000002",
      "status": "COMPLETED",
      "failed_reason": null,
      "elevenlabs_analysis": {
        "was_success": "success",
        "termination_reason": "Client disconnected: 1000",
        "summary": "Sarah de Eurofirms llama a Elena para confirmar...",
        "evaluation_criteria": [
          {
            "criteria_id": "call_evaluation",
            "result": "success",
            "rationale": "El agente ofrecio el turno y el usuario confirmo."
          }
        ],
        "data_collection": [],
        "dynamic_vars": {
          "system__call_sid": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
          "system__conversation_id": "conv_9801kjrejzrrede8b8zsy3tgj3xd",
          "system__call_duration_secs": 66,
          "system__caller_id": "+34600000002",
          "system__called_number": "3232",
          "system__agent_id": "agent_5601kj8tx92bff28rnn1djcjys45",
          "system__time_utc": "2026-03-02T23:38:04.880372+00:00",
          "system__timezone": "Europe/Madrid"
        },
        "conversation_id": "conv_9801kjrejzrrede8b8zsy3tgj3xd",
        "base64_audio": "<string base64 MP3 o null>"
      }
    }
  },
  "last_updated_at": "2026-03-03 00:37:55"
}
```

#### Campos del reporte final

| Campo | Tipo | Requerido | Descripcion |
|-------|------|-----------|-------------|
| `call_id` | UUID | Si | ID de la llamada |
| `type` | string | Si | Siempre `"final"` |
| `status` | string | Si | `"COMPLETED"` (exito) o `"FAILED"` (todos fallaron) |
| `call_context` | object | No | Contexto del turno |
| `call_record` | object | Si | Contiene SOLO el ultimo numero intentado. La key es dinamica (ej: `"alternative_phone"`, `"main_phone"`) |
| `last_updated_at` | string | No | Timestamp de ultima modificacion |

#### Campos de `call_context`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `confirmation` | string | Decision verbal: `"Turno confirmado"`, `"Turno rechazado"`, `"No confirmado"` |
| `worker_name` | string | Nombre completo del trabajador |
| `worker_first_name` | string | Nombre de pila |
| `position` | string | Puesto de trabajo |
| `work_center` | string | Centro de trabajo |
| `address` | string | Direccion |
| `shift_date` | string | Fecha del turno |
| `shift_start_time` | string | Hora inicio |
| `shift_end_time` | string | Hora fin |
| `hourly_rate` | string | Tarifa por hora |
| `instructions` | string | Instrucciones adicionales |

#### Campos de `call_record`

El objeto `call_record` tiene una key dinamica (el nombre del telefono que se uso). El valor es un `phone_record` con la misma estructura que en el reporte parcial.

---

## Respuestas

### Exito (200)

```json
{
  "success": true,
  "data": {
    "id": "uuid-del-intento",
    "callRequestId": "uuid-del-call-request",
    "attemptNumber": 1,
    "phoneUsed": "+34600000001",
    "technicalResult": "failed",
    "summary": "La llamada fue atendida por un contestador automatico.",
    "failedReason": "AST_ISSUE",
    "elevenlabsConversationId": "conv_abc123",
    "audioUrl": "https://...",
    "durationSeconds": 12,
    "createdAt": "2026-03-06T10:30:00.000Z"
  }
}
```

### Errores

| Codigo | Descripcion |
|--------|-------------|
| 401 | `Auth-Token` invalido o ausente |
| 404 | `call_id` no encontrado en el sistema |
| 400 | Payload invalido (campos faltantes o formato incorrecto) |

---

## Ejemplo con cURL

### Reporte parcial

```bash
curl -X POST https://<HOST>/api/call-requests/webhook/call-report \
  -H "Content-Type: application/json" \
  -H "Auth-Token: 435kjo3h4p6h34p56hbñlkn345h6IUGOUBJ" \
  -d '{
    "call_id": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
    "type": "partial",
    "phone_record": {
      "number": "+34600000001",
      "status": "FAILED",
      "failed_reason": "voicemail_detected",
      "elevenlabs_analysis": null
    }
  }'
```

### Reporte final

```bash
curl -X POST https://<HOST>/api/call-requests/webhook/call-report \
  -H "Content-Type: application/json" \
  -H "Auth-Token: 435kjo3h4p6h34p56hbñlkn345h6IUGOUBJ" \
  -d '{
    "call_id": "7ccfbb6a-4cdf-43c5-b98a-3a6ae2887074",
    "type": "final",
    "status": "COMPLETED",
    "call_context": {
      "confirmation": "Turno confirmado"
    },
    "call_record": {
      "main_phone": {
        "number": "+34600000001",
        "status": "COMPLETED",
        "failed_reason": null,
        "elevenlabs_analysis": {
          "was_success": "success",
          "summary": "El trabajador confirmo asistencia al turno.",
          "conversation_id": "conv_abc123",
          "base64_audio": null
        }
      }
    }
  }'
```

---

## Notas importantes

1. **`call_id`** es el mismo UUID que se envio como `id` al programar la llamada en `/calls/add`
2. Los reportes **parciales** se envian antes que el **final** — cada fallo intermedio genera un parcial
3. El **final** solo incluye el ultimo numero intentado; los anteriores ya fueron reportados como parciales
4. El `base64_audio` puede ser muy grande; se acepta `null` si el audio no esta disponible
5. El `elevenlabs_analysis` puede ser `null` si la llamada no llego a conectar con ElevenLabs (fallos de Asterisk)
6. El numero de intento (`attemptNumber`) se calcula automaticamente en el servidor — no necesitan enviarlo
