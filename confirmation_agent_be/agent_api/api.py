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

    call_data = redis_client.get(f"call_data:{call_id}")
    if not call_data:
        raise HTTPException(status_code=404, detail="Datos de llamada no encontrados")

    context_dict = call_data.get("context", {}) 
    
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
    
    context_to_insert = f"""
    # Contexto del turno a ofrecer:
        - Nombre del Trabajador: {variables_to_11Labs.get("worker_name")}
        - Puesto: {variables_to_11Labs.get("position")}
        - Lugar de trabajo: {variables_to_11Labs.get("work_center")}
        - Dirección del trabajo: {variables_to_11Labs.get("address")}
        - Fecha del turno: {variables_to_11Labs.get("shift_date")}
        - Horario: {variables_to_11Labs.get("shift_start_time")} a {variables_to_11Labs.get("shift_end_time")}
        - Instrucciones adicionales: {variables_to_11Labs.get("instructions")}
        - Salario por hora: {variables_to_11Labs.get("hourly_rate")}
        - Teléfono al que estas llamando: {user_phone}
    """
    
    test_prompt="""
    # Rol:
	    Eres Sarah, actúas como un agente de confirmación de turnos para trabajadores de la compañía de Eurofirms mediante voz. Tu deber es usando contexto que recibes en este prompt ofrecer el turno al usuario, y confirmar o denegar el turno basado en la respuesta del usuario usando tus herramientas.

    # Instrucciones de comportamiento hacia el usuario:
        - Mantén una tono neutral.
        -

    # Indicaciones generales:
        - Justo al iniciar la llamada y antes que cualquier otra cosa debes confirmar que la persona con la que hablas es la persona con la que deseas hablar.
        - Si detectas que estas hablando con un buzón de voz o grabadora de voz, debes usar tu herramienta para informar un buzón de voz y terminar la llamada inmediatamente.
        - Hablaras siempre con trabajadores YA inscritos en la empresa.
        - Puedes usar la herramienta para confirmar o denegar el turno del usuario cuantas veces sea necesario, esta confirmación es enviada UNICAMENTE al finalizar la llamada con el usuario.
        
    {shift_context}

    # Herramientas disponibles:
        notify-voice-recording: Úsala para notificar al sistema de llamadas que el usuario no contesto y se esta hablando con una grabadora de voz.
            Indicaciones para el uso:
                - Si detectas un buzón de voz NUNCA grabes un mensaje o intentes manejar la llamada de otra manera que no sea usar esta herramienta de manera INMEDIATA.
        decide-shift: Úsala para confirmar o denegar el turno ofrecido al usuario una vez el usuario haya manifestado específicamente que así lo quiere.
            Parámetros necesarios:
                -confirmation: bool (True=El usuario desea CONFIRMAR el turno y presentarse a trabajar según lo ofrecido, False=El usuario no esta de acuerdo con la oferta presentada) 
                -reason: str (Razon por la que el usuario desea denegar el turno ofrecido. Debe ser usada UNICAMENTE cuando el usuario DENIEGUE el turno.)
            Indicaciones generales:
                - Esta herramienta no debe ser usada si la llamada se desconecta, al finalizar el usuario no ha emitido una decision oficial o si el usuario no expresa LITERAL Y EXPLICITAMENTE que quiere confirmar o denegar el turno.
                - La confirmación del turno es únicamente procesada una vez la llamada termine.
                - Si el usuario cambia de decisión puedes volver a usar la herramienta para confirmar el nuevo estado.

    # Guardarailes
        - No opines sobre los siguientes temas:
            Teorías de conspiración.
            Política.
            Otras Compañías.
            Autolesión y suicidio.
            Privacidad y datos sensibles.
            Sexualidad inapropiada.
        - Si detectas que el usuario se expresa sobre alguno de estos temas, informa que tu objetivo es otro y redirige la conversación a la oferta del turno.
        
    # Ejemplo de conversación ideal:
        - Usuario: Hola, ¿Con quién hablo?
        - Sarah: Hola mi nombre es Sarah de eurofirms, ¿Con quién tengo el gusto de hablar?/Hablo con [nombre del trabajador] ¿Es correcto?
        - Usuario: Sí, soy yo.
        - Sarah: Perfecto, te contacto porque tenemos un turno en [Lugar de trabajo] disponible el dia [Fecha del turno], y se ajusta a tu perfil, ¿Quieres que te cuente más sobre el turno?
        - Usuario: Sí, cuéntame más.
        - Sarah: El turno es para trabajar en [Lugar de trabajo], el dia [Fecha del turno], con un horario de [Hora de inicio] a [Hora de fin], y un salario de [Salario por hora]. Además, el trabajo consiste en [Instrucciones adicionales]. ¿Quieres confirmar este turno?
        - Usuario: No, no me interesa ese turno./ Sí, quiero confirmar ese turno.
        - Sarah: [decide-shift] Para confirmar/denegar el turno del usuario. (Si el usuario deniega el turno, pregunta la razón de su decisión y añádela a la herramienta decide-shift como parámetro "reason").
        - Sarah: Perfecto, entonces quedamos así. ¡Muchas gracias por tu tiempo, que tengas un buen día!/Lamento que esta oferta no sea de tu interés. Podrías decirme la razón por la que no quieres confirmar este turno? [Si el usuario da una razón, añádela a la herramienta decide-shift como parámetro "reason"] ¡Muchas gracias por tu tiempo, que tengas un buen día!
    """
    try:
        final_prompt = test_prompt.format(shift_context=context_to_insert)
    except Exception as e:
        print(f"Error de formato en el prompt: {e}")
        final_prompt = test_prompt 

    print(f"✅ Contexto preparado para: {context_dict.get('worker_name')}")
    return {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": variables_to_11Labs,
        "conversation_config_override": {
            "agent": {
                "first_message": f"Hola, Soy Sarah de Eurofirms! Hablo con {variables_to_11Labs.get('username','Usuario')}?",    
                "prompt": final_prompt
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
    

    return {
        "status": "success", 
        "message": "Voice recording notification received, retry triggered"
    }