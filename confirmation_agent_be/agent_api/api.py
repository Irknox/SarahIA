import sys
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException, Header, Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_call_context
from typing import Dict, Any, Optional
import redis
import json
import hmac
import hashlib
from datetime import datetime


load_dotenv()
Token_API=os.environ.get('NEXT_PUBLIC_AUTH_TOKEN')
REDIS_URL = os.getenv("REDIS_URL", "redis://:password@127.0.0.1:6380/0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


app = FastAPI(title="SarahAI API")


##-----------------------Tools----------------##
async def applyDecision(params):    
    confirmation = params.get("confirmation") 
    call_id = params.get("call_id")
    
    if not call_id:
        raise HTTPException(status_code=400, detail="Falta call_id")

    raw_data = redis_client.get(f"call_data:{call_id}")
    if not raw_data:
        raise HTTPException(status_code=404, detail="Datos de llamada no encontrados")

    call_data = json.loads(raw_data)
    
    call_data["context"]["confirmation"] = confirmation
    
    call_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    redis_client.set(f"call_data:{call_id}", json.dumps(call_data), ex=86400)
    
    print(f"[Tool] Decisión '{confirmation}' aplicada para ID {call_id}.")

    return {
        "status": "success", 
        "message": f"Decisión {confirmation} registrada"
    }


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

    return {
        "type": "conversation_initiation_client_data",
        "conversation_config_override": {
            "agent": {
        "prompt": {
            "prompt": agent_instructions,
        },
        "first_message": f"Hola mi nombre es Sarah de Eurofirms, estoy hablando con {variables_to_11Labs.get('username')}?",
    },
            
        }
    } 

WEBHOOK_SECRET=os.environ.get("ELEVENLABS_WEBHOOK_SIGNATURE")
@app.post("/webhooks/elevenlabs-post-call")
async def elevenlabs_post_call_webhook(request: Request):
    payload_raw = await request.body()
    signature_header = request.headers.get("elevenlabs-signature") 
    if not signature_header:
        print("🔴 Webhook recibido sin firma")
        raise HTTPException(status_code=401, detail="Missing signature")
    try:
        parts = dict(x.split('=') for x in signature_header.split(','))
        timestamp = parts.get('t')
        received_hash = parts.get('v0')
        signed_payload = f"{timestamp}.{payload_raw.decode('utf-8')}"
        
        expected_hash = hmac.new(
            WEBHOOK_SECRET.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(received_hash, expected_hash):
            print("❌ Firma de Webhook inválida")
            raise HTTPException(status_code=401, detail="Invalid signature")
    except Exception as e:
        print(f"⚠️ Error al validar firma: {e}")
        raise HTTPException(status_code=401, detail="Signature validation failed")
    payload = json.loads(payload_raw)
    print(f"✅ Webhook post-llamada recibido y validado: {payload}")
    event_type = payload.get("type")
    data = payload.get("data", {})
    
    if event_type == "call_initiation_failure":
        print (f"Falla en inicio de llamada reportado desde el webhook :{data}")
        
        return {"status": "received"}
    elif event_type == "post_call_audio":
        conversation_id=data.get("conversation_id","No disponible")
        print (f"Audio recibido post llamada conversacion :{conversation_id}")
        audio_data =data.get("full_audio", "No disponible")

        call_id = None
        for key in redis_client.scan_iter("call_data:*"):
            raw_redis_data = redis_client.get(key)
            if raw_redis_data:
                try:
                    call_data = json.loads(raw_redis_data)
                    call_record = call_data.get("call_record", {})
                    last_called_attr = call_record.get("last_called", "phone")
                    
                    if last_called_attr in call_record:
                        current_attr_data = call_record[last_called_attr]
                        
                        if "elevenlabs_analysis" in current_attr_data:
                            stored_conversation_id = current_attr_data["elevenlabs_analysis"].get("conversation_id")
                            
                            if stored_conversation_id == conversation_id:
                                call_id = key.split(":")[1]
                                current_attr_data["elevenlabs_analysis"]["base64_audio"] = audio_data
                                redis_client.set(key, json.dumps(call_data), ex=86400)
                                print(f"✅ Audio base64 agregado al análisis para {conversation_id} (call_id: {call_id})")
                                break
                except json.JSONDecodeError:
                    continue
        
        if not call_id:
            print(f"⚠️ No se encontró call_id para conversation_id: {conversation_id}")
        
        return {"status": "received"}
    
    
    elif event_type == "post_call_transcription":
        metadata = data.get("metadata", {})
        phone_call = data.get("user_id", {})
        conversation_id=data.get("conversation_id", "")
        
        call_id = phone_call.get("call_sid") 
        phone_number=phone_call.get("external_number")
        termination_reason = metadata.get("termination_reason") 
        
        if not call_id:
            print("🔴 Error: No se encontró call_sid en el payload")
            return {"status": "error", "message": "No call_sid found"}
        
        
        analysis_data = data.get("analysis", {})
        is_success = analysis_data.get("call_successful", "No dispible")
        print(f"Analisis de 11labs recibido: {analysis_data}")
        conversation_initiation_client_data=analysis_data.get("conversation_initiation_client_data", "No Disponible")
        dynamic_vars=conversation_initiation_client_data.get("dynamic_variables","No Disponible")
        evaluation_result=analysis_data.get("evaluation_criteria_results_list", "No disponible"),
        data_collection_results_list=analysis_data.get("data_collection_results_list", "No disponible")
        transcript_summary= analysis_data.get("transcript_summary", "")
        
        elevenlabs_analysis = {
            "was_success": is_success, 
            "termination_reason": termination_reason,        
            "summary": transcript_summary,
            "evaluation_criteria": evaluation_result,       
            "data_collection": data_collection_results_list,
            "dynamic_vars": dynamic_vars,
            "conversation_id": conversation_id
        }

        raw_redis_data = redis_client.get(f"call_data:{call_id}")
        if not raw_redis_data:
            return {"status": "error", "message": "Call not found in Redis"}

        full_call_data = json.loads(raw_redis_data)
        call_record = full_call_data.get("call_record", {})
        last_called_attr = call_record.get("last_called", "phone")

        if last_called_attr in call_record:
            call_record[last_called_attr]["elevenlabs_analysis"] = elevenlabs_analysis
            full_call_data["call_record"] = call_record
            
            redis_client.set(f"call_data:{call_id}", json.dumps(full_call_data), ex=86400)
            print(f"✅ Análisis guardado para {call_id} en el registro '{last_called_attr}'")
            
        if is_success=="success":
            print (f"✅ Flujo de llamada exitosa, oferta ofrecida y respondida")
            redis_client.set(f"call_status:{call_id}", "COMPLETED", ex=86400)
        
        elif is_success=="failure":
            print (f"❌ Flujo de llamada fallido para {call_id} con numero : {phone_number}")
            redis_client.set(f"call_status:{call_id}", "FAILED", ex=86400)
        return {"status": "received"}
    
    
    elif event_type == "call_initiation_failure":
        reason=data.get("failure_reason","No disponible")
        phone_called = data.get("user_id", "No disponible")
        raw_data = redis_client.get(f"call_data:{call_id}")
        if not raw_data:
            return {"status": "error", "message": "Call not found in Redis"}
        
        call_data = json.loads(raw_data)
        call_record = call_data.get("call_record", {})
        
        target_attr = None
        for attr in ["phone", "alternative_phone", "alternative_phone_2"]:
            if call_record.get(attr, {}).get("number") == phone_called:
                target_attr = attr
                break
        
        if target_attr:
            was_already_failed = call_record[target_attr].get("status") == "FAILED"

            call_record[target_attr]["status"] = "FAILED"
            call_record[target_attr]["failed_reason"] = reason
            
            if not was_already_failed:
                redis_client.set(f"call_status:{call_id}", "FAILED", ex=86400)
                print(f"[Webhook] call_initiation_failure: {phone_called} marcado como FAILED. Status global actualizado.")
            else:
                print(f"[Webhook] call_initiation_failure: {phone_called} ya estaba FAILED. Solo razón actualizada.")
            
            call_data["call_record"] = call_record
            redis_client.set(f"call_data:{call_id}", json.dumps(call_data), ex=86400)
            
            return {"status": "received"}
        else:
            print(f"⚠️ No se encontró el teléfono {phone_called} en call_record")
            return {"status": "error", "message": "Teléfono no encontrado en registro"}
        
                              

##---------------------------------Tools de ElevenLabs ---------------------------------##
@app.post("/webhooks/call-issue-detected")
async def notify_call_issue(
    request: Request,    
    auth_token: Optional[str] = Header(None, alias="auth-token")
):
    if auth_token != Token_API:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    payload = await request.json() 
    call_params = payload.get("call_info", {})
    reason = payload.get("reason", "IA detectó buzón de voz")
    call_id = call_params.get("call_id")
    phone_reported = call_params.get("phone")
    
    raw_data = redis_client.get(f"call_data:{call_id}")
    if not raw_data:
        raise HTTPException(status_code=404, detail="Llamada no encontrada")
    
    call_data = json.loads(raw_data)
    call_record = call_data.get("call_record", {})
    
    target_attr = None
    for attr in ["phone", "alternative_phone", "alternative_phone_2"]:
        if call_data.get(attr) == phone_reported:
            target_attr = attr
            break

    if not target_attr:
        return {"status": "error", "message": "Número no reconocido"}

    already_failed = False
    if target_attr in call_record and call_record[target_attr].get("status") in ["FAILED", "BUSY", "NOANSWER", "FAILED_AST"]:
        already_failed = True

    if already_failed:
        call_record[target_attr]["failed_reason"] = f"{reason} (Confirmado por IA)"
    else:
        call_record[target_attr] = {
            "number": phone_reported,
            "status": "FAILED",
            "failed_reason": reason
        }
        #redis_client.set(f"call_status:{call_id}", "FAILED", ex=86400)
        print(f"[Webhook] IA reporta fallo primero para {phone_reported}. Marcando FAILED global.")

    call_data["call_record"] = call_record
    redis_client.set(f"call_data:{call_id}", json.dumps(call_data), ex=86400)
    
    return {"status": "success"}


@app.post("/tools")
async def tools_endpoint(
        request: Request,    
        auth_token: Optional[str] = Header(None, alias="auth-token")
    ):
    if auth_token != Token_API:
        print(f"Intento de acceso no autorizado con token: {auth_token}")
        raise HTTPException(status_code=401, detail="No autorizado: Token inválido")
    
    payload = await request.json()
    print(f"🧰 Tool solicitada por agente: {payload}")
    
    tool_request=payload.get("tool")
    params=payload.get("params", {})

    if tool_request=="applyDecision":
        return await applyDecision(params)


    
