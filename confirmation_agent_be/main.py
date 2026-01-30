import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException,Header,Depends
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import leer_db, guardar_db, agregar_llamada, actualizar_llamada, eliminar_llamada
from tasks import celery_app, disparar_llamada_ami 
import pytz

madrid_tz = pytz.timezone("Europe/Madrid")

load_dotenv()
TOKEN = os.getenv("AUTH_TOKEN")

async def verify_token(auth_token: str = Header(None)):
    if auth_token != TOKEN:
        raise HTTPException(status_code=401, detail="Token de autorización inválido o ausente")
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

class RegistroLlamada(BaseModel):
    username: str
    email: str
    phone: str
    type: str
    status: str
    date: str

@app.get("/")
def read_root():
    return {"message": "SilverAI API is running"}


@app.get("/calls", dependencies=[Depends(verify_token)])
def get_calls(auth_token: str = Header(None)):
    if auth_token != TOKEN:
        raise HTTPException(status_code=401, detail="Token de autorización inválido o ausente")
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
    """
    Agenda una nueva llamada en Celery y guarda el registro en db.json
    """
    try:
        naive_dt = datetime.strptime(data.date.strip(), "%Y-%m-%d %H:%M:%S")
        local_dt = madrid_tz.localize(naive_dt)
        task = disparar_llamada_ami.apply_async(
            args=[data.phone, "101"],
            eta=local_dt
        )
        nueva_entrada = {
            "username": data.username,
            "email": data.email,
            "phone": data.phone,
            "type": data.type,
            "status": "Agendado",
            "date": data.date,
            "task_id": task.id
        }
        registro_creado = agregar_llamada(nueva_entrada)
        return {
            "status": "success", 
            "message": f"Llamada agendada para {data.username} a las {data.date} (Madrid)", 
            "task_id": task.id,
            "data": registro_creado
        }   
    except Exception as e:
        print(f"Error en schedule_call: {e}")
        raise HTTPException(status_code=500, detail=f"Error al agendar: {str(e)}")
    
@app.put("/calls/update/{call_id}", dependencies=[Depends(verify_token)])
async def update_call_record(call_id: int, data: RegistroLlamada):
    db = leer_db()
    llamada_previa = next((item for item in db if item["id"] == call_id), None)
    if not llamada_previa:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    if "task_id" in llamada_previa and llamada_previa["task_id"]:
        celery_app.control.revoke(llamada_previa["task_id"], terminate=True)

    try:
        naive_dt = datetime.strptime(data.date.strip(), "%Y-%m-%d %H:%M:%S")
        local_dt = madrid_tz.localize(naive_dt)
        task = disparar_llamada_ami.apply_async(
            args=[data.phone, "101"],
            eta=local_dt
        )

        update_data = data.model_dump()
        update_data["task_id"] = task.id
        actualizar_llamada(call_id, update_data)
        return {"status": "success", "task_id": task.id}
    except Exception as e:
        actualizar_llamada(call_id, data.model_dump())
        return {"status": "warning", "detail": str(e)}

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