import os
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import leer_db, agregar_llamada, actualizar_llamada, eliminar_llamada
from tasks import redis_client

load_dotenv()
TOKEN = os.getenv("NEXT_PUBLIC_AUTH_TOKEN")
AMI_EXTENSION = os.getenv("AMI_EXTENSION")

async def verify_token(auth_token: str = Header(None, alias="Auth-Token")):
    if auth_token != TOKEN:
        raise HTTPException(
            status_code=401, 
            detail="Token de autorización inválido o ausente"
        )
    return auth_token

origins = [
    "http://localhost:7777",
    "http://127.0.0.1:7777",
    "http://64.23.170.136:7373"
]

app = FastAPI(title="SarahAI Calling System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           
    allow_credentials=True,
    allow_methods=["*"],               
    allow_headers=["*"],              
)

class ContextoLlamada(BaseModel):
    worker_name: str
    worker_first_name: str
    worker_language: str
    position: str
    work_center: str
    address: str
    shift_date: str
    shift_date_raw: str
    shift_start_time: str
    shift_end_time: str
    instructions: str
    hourly_rate: str
    call_request_id: str
    confirmation: Optional[str] = "No confirmado"

class RegistroLlamada(BaseModel):
    id: str
    phone: str
    alternative_phone: str
    alternative_phone_2: str
    date: str
    context: ContextoLlamada 
    agent_instructions: str  

@app.get("/")
def read_root():
    return {"message": "SilverAI API is running"}


@app.get("/calls", dependencies=[Depends(verify_token)])
def get_calls():
    return leer_db()

class LlamadaSchema(BaseModel):
    username: str
    email: str
    phone: str
    type: str
    agent_ext: str = "9998"
    scheduled_time: datetime 

@app.post("/calls/add", dependencies=[Depends(verify_token)])
async def schedule_call(data: RegistroLlamada):
    try:
        print(f" Data recibida para agendar llamada: {data}")
        pending_data = {
            "phone": data.phone,
            "alternative_phone": data.alternative_phone,
            "alternative_phone_2": data.alternative_phone_2,
            "agent_ext": AMI_EXTENSION,
            "scheduled_time": data.date.strip(),
            "context": data.context.model_dump(),
            "agent_instructions": data.agent_instructions
        }
        redis_client.set(f"pending_call:{data.id}", json.dumps(pending_data), ex=86400)
        return {
            "status": "success",
            "message": f"Llamada ID {data.id} agendada para las {data.date}"
        }
    except Exception as e:
        print(f"Error en schedule_call: {e}")
        raise HTTPException(status_code=500, detail=f"Error al agendar: {str(e)}")
    
@app.put("/calls/update/{call_id}", dependencies=[Depends(verify_token)])
async def update_call_record(call_id: int, data: RegistroLlamada):
    try:
        redis_client.delete(f"pending_call:{call_id}")
        pending_data = {
            "phone": data.phone,
            "alternative_phone": data.alternative_phone,
            "alternative_phone_2": data.alternative_phone_2,
            "agent_ext": AMI_EXTENSION,
            "scheduled_time": data.date.strip(),
            "context": data.context.model_dump(),
            "agent_instructions": data.agent_instructions
        }
        redis_client.set(f"pending_call:{call_id}", json.dumps(pending_data), ex=86400)
        actualizar_llamada(call_id, data.model_dump())
        return {"status": "success", "message": f"Llamada {call_id} actualizada"}
    except Exception as e:
        actualizar_llamada(call_id, data.model_dump())
        return {"status": "warning", "detail": str(e)}

@app.delete("/calls/delete/{call_id}", dependencies=[Depends(verify_token)])
async def delete_call_record_prod(call_id: int):
    """
    Elimina un registro de producción y limpia Redis.
    """
    redis_client.delete(f"pending_call:{call_id}")
    exito = eliminar_llamada(call_id)

    if not exito:
        raise HTTPException(status_code=500, detail="Error al eliminar el registro de la base de datos")

    return {"status": "success", "message": f"Registro {call_id} y su tarea asociada han sido eliminados"}

#------------------------------Development Endpoints------------------------------#
@app.post("/calls/add/dev", dependencies=[Depends(verify_token)])
async def add_call_record(data: RegistroLlamada):
    """Agrega un registro nuevo al db.json"""
    try:
        nueva = agregar_llamada(data.model_dump())
        return {"status": "success", "data": nueva}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/calls/update/dev/{call_id}", dependencies=[Depends(verify_token)])
async def update_call_record(call_id: int, data: RegistroLlamada):
    """Actualiza un registro existente por su ID"""
    exito = actualizar_llamada(call_id, data.model_dump())
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"status": "success", "message": "Registro actualizado"}

@app.delete("/calls/delete/dev/{call_id}", dependencies=[Depends(verify_token)])
async def delete_call_record(call_id: int):
    """Elimina un registro del db.json por su ID"""
    exito = eliminar_llamada(call_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"status": "success", "message": "Registro eliminado"}
