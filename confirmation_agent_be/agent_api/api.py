
import sys
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException, Header, Request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_call_context
from typing import Dict, Any, Optional
from utils import get_call_context


load_dotenv()
Token_API=os.environ.get('NEXT_PUBLIC_AUTH_TOKEN')

app = FastAPI(title="SarahAI API")

@app.post("/webhooks/elevenlabs-pre-call")
async def elevenlabs_pre_call_webhook(
        request: Request,    
        auth_token: Optional[str] = Header(None, alias="auth_token")
    ):
    if auth_token != Token_API:
        print(f"Intento de acceso no autorizado con token: {auth_token}")
        raise HTTPException(status_code=401, detail="No autorizado: Token inválido")
    payload = await request.json()
    print(f"📲 Webhook pre-llamada recibido: {payload}")
    caller_id = payload.get("caller_id", "")
    call_id=payload.get("conversation_id", "")
    call_context= get_call_context(caller_id, call_id)
    username=call_context.get("username")
    email=call_context.get("email")
    type=call_context.get("type")
    indications=call_context.get("indications")
    print(f"Contexto para la llamada del usuario {username}: {call_context}")
    return {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": {
            "user_name": username,
            "type": type,
            "indications": indications,
        },
        "conversation_config_override": {
            "agent": {
                "first_message": f"Hola {username}, soy Silver de Moovin! ¿Cómo puedo ayudarte hoy?"
            }
        }
    } 
