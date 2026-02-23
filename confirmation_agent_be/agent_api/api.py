import sys
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException, Header, Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_call_context
from typing import Dict, Any, Optional
import redis
import json

load_dotenv()
Token_API=os.environ.get('NEXT_PUBLIC_AUTH_TOKEN')
REDIS_URL = os.getenv("REDIS_URL", "redis://:password@127.0.0.1:6380/0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


app = FastAPI(title="SarahAI API")

##---------------------------------Webhooks para ElevenLabs ---------------------------------##
@app.post("/webhooks/elevenlabs-pre-call")
async def elevenlabs_pre_call_webhook(
request: Request,    
        auth_token: Optional[str] = Header(None, alias="auth-token")
    ):
    if auth_token != Token_API:
        print(f"Intento de acceso no autorizado con token: {auth_token}")
        raise HTTPException(status_code=401, detail="No autorizado: Token inválido")
    
    payload = await request.json()
    print(f"📲 Webhook pre-llamada recibido: {payload}")
    
    user_phone = payload.get("caller_id")
    call_id = payload.get("call_sid")
    if not call_id:
        raise HTTPException(status_code=400, detail="Falta conversation_id")

    call_data_raw = redis_client.get(f"call_data:{call_id}")
    
    if not call_data_raw:
        raise HTTPException(status_code=404, detail="Datos de llamada no encontrados")
    
    try:
        call_data = json.loads(call_data_raw)
    except json.JSONDecodeError:
        print(f"❌ Error decodificando JSON de Redis para ID: {call_id}")
        raise HTTPException(status_code=500, detail="Error interno de datos")

    context_dict = call_data.get("context", {}) 
    
    agent_instructions = call_data.get("agent_instructions", "No hay instrucciones específicas para el agente.")
    

    print(f"✅ Instrucciones para llamada({type(agent_instructions)}): {agent_instructions}")
    
    variables_to_11Labs = {
        "username": context_dict.get("worker_first_name", "Trabajador"),
        "worker_name": context_dict.get("worker_name", "No disponible"),
        "position": context_dict.get("position", "No disponible"),
        "work_center": context_dict.get("work_center", "No disponible"),
        "address": context_dict.get("address", "No disponible"),
        "shift_date": context_dict.get("shift_date", "No disponible"),
        "shift_start_time": context_dict.get("shift_start_time", "No disponible"),
        "shift_end_time": context_dict.get("shift_end_time", "No disponible"),
        "instructions": context_dict.get("instructions", "No disponible"),
        "hourly_rate": context_dict.get("hourly_rate", "No disponible"),
    }

    print(f"✅ Contexto preparado para: {context_dict.get('worker_name')}")
    
    return {
        "type": "conversation_initiation_client_data",
        "conversation_config_override": {
            "agent": {
                "prompt": "Eres un agente de llamadas para una farmacia de nombre farmacoop",
                "first_message": f"Hola, Soy Sarah de farmacoop! ¿Tengo el gusto de hablar con Alejandro?"
            }
        }
    } 


##---------------------------------Tools de ElevenLabs ---------------------------------##
@app.post("/webhooks/voice-recording")
async def notify_voice_recording(
        request: Request,    
        auth_token: Optional[str] = Header(None, alias="auth-token")
    ):
    if auth_token != Token_API:
        print(f"Intento de acceso no autorizado con token: {auth_token}")
        raise HTTPException(status_code=401, detail="No autorizado: Token inválido")
    
    payload = await request.json()
    call_id = payload.get("system__conversation_id")
    
    if not call_id:
        raise HTTPException(status_code=400, detail="Falta conversation_id")

    status_key = f"call_status:{call_id}"
    if not redis_client.exists(status_key):
        return {"status": "error", "message": "ID de llamada no encontrado en Redis"}

    redis_client.set(status_key, "FAILED", ex=86400)
    
    print(f"[Webhook] Buzón detectado en ID {call_id}. Forzando reintento vía Celery Beat.")

    return {
        "status": "success", 
        "message": "Voice recording notification received, retry triggered"
    }
    

@app.post("/tools/set-decision")
async def applyDecision(
        request: Request,    
        auth_token: Optional[str] = Header(None, alias="auth-token")
    ):
    if auth_token != Token_API:
        print(f"Intento de acceso no autorizado con token: {auth_token}")
        raise HTTPException(status_code=401, detail="No autorizado: Token inválido")
    
    payload = await request.json()
    print(f"📲 Webhook pre-llamada recibido: {payload}")
    
    user_phone = payload.get("caller_id")
    call_id = payload.get("system__conversation_id")
    
    if not call_id:
        raise HTTPException(status_code=400, detail="Falta conversation_id")

    call_data = redis_client.get(f"call_data:{call_id}")
    if not call_data:
        raise HTTPException(status_code=404, detail="Datos de llamada no encontrados")

    context_dict = call_data.get("context", {}) 
    
    context_dict["confirmation"] = payload.get("confirmation", False)
    
    redis_client.hset(f"call_data:{call_id}", "context", json.dumps(context_dict))
    
    
    print(f"[Tool] Decisión aplicada para ID {call_id}. Contexto actualizado")
    
    ##outcome es el nombre status en la tabla persistente

    return {
        "status": "success", 
        "message": "Voice recording notification received, retry triggered"
    }