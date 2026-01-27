import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import leer_db, guardar_db

load_dotenv()

app = FastAPI(title="SarahAI Calling System")

class LlamadaSchema(BaseModel):
    user_name: str
    phone: str
    agent_ext: str = "9998"
    scheduled_time: Optional[datetime] = None 

@app.get("/")
def read_root():
    return {"message": "SilverAI API is running"}

@app.get("/calls")
def get_calls():
    return leer_db()

@app.post("/schedule-call")
async def schedule_call(data: LlamadaSchema):
    from tasks import disparar_llamada_ami
    import pytz
    
    try:
        if data.scheduled_time:
            if data.scheduled_time.tzinfo is None:
                madrid_tz = pytz.timezone("Europe/Madrid")
                data.scheduled_time = madrid_tz.localize(data.scheduled_time)
            task = disparar_llamada_ami.apply_async(
                args=[data.phone, data.agent_ext],
                eta=data.scheduled_time
            )
            status_msg = f"Llamada agendada para {data.scheduled_time}"
        else:
            task = disparar_llamada_ami.delay(data.phone, data.agent_ext)
            status_msg = "Llamada disparada inmediatamente"
        db_actual = leer_db()
        new_entry = {
            "id": len(db_actual) + 1,
            "user": data.user_name,
            "phone": data.phone,
            "agent_ext": data.agent_ext,
            "scheduled": data.scheduled_time.strftime("%Y-%m-%d %H:%M:%S") if data.scheduled_time else "NOW",
            "task_id": task.id,
            "status": "scheduled" if data.scheduled_time else "completed"
        }
        db_actual.append(new_entry)
        guardar_db(db_actual)
        return {"status": "success", "message": status_msg, "task_id": task.id}
    except Exception as e:
        print(f"Error en schedule_call: {e}")
        raise HTTPException(status_code=500, detail=str(e))