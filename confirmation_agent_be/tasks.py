import os
import requests
from celery import Celery
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils import leer_db, guardar_db, send_call_report
import redis
import json

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://:password@127.0.0.1:6380/0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


celery_app = Celery(
    "Sarah_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Madrid',  
    enable_utc=False,
    task_acks_late=True,            
    task_ignore_result=True,        
    result_expires=3600,
    task_reject_on_worker_lost=True,
    broker_transport_options={
        'visibility_timeout': 3600   
    }
)

celery_app.conf.beat_schedule = {
    'sincronizar-estados-redis-db': {
        'task': 'sync_call_status',
        'schedule': 15.0, 
    },
}

AMI_CONTROL_URL = os.getenv("AMI_URL",)
AMI_TOKEN = os.getenv("AMI_CONTROL_TOKEN")
AMI_EXTENSION=os.getenv('AMI_EXTENSION')

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def disparar_llamada_ami(self, user_phone, alternative_phone, alternative_phone_2, agent_ext, call_id, context=None, agent_instructions=None):
    """
    Tarea de disparo. Almacena TODO el contexto en Redis antes de llamar.
    """
    payload = {
        "user_phone": user_phone,
        "agent_ext": agent_ext,
        "call_id": str(call_id)
    }
    headers = {
        "x-ari-control-token": AMI_TOKEN,
        "Content-Type": "application/json"
    }
    try:
        existing_data = redis_client.get(f"call_data:{call_id}")
        
        if existing_data:
            info = json.loads(existing_data)
            info["status"] = "DISPATCHED"
            info["last_called_number"] = user_phone
            if context: info["context"] = context
            if agent_instructions: info["agent_instructions"] = agent_instructions
        else:
            info = {
                "status": "DISPATCHED",
                "phone": user_phone,
                "alternative_phone": alternative_phone,
                "alternative_phone_2": alternative_phone_2,
                "call_record": { 
                    "last_called": "phone",
                    "phone": { 
                        "number": user_phone,
                        "status": "DISPATCHED",
                        "failed_reason": None
                    },  
                },
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "context": context,             
                "agent_instructions": agent_instructions 
            }
        redis_client.set(f"call_data:{call_id}", json.dumps(info), ex=86400)
        redis_client.set(f"call_status:{call_id}", "DISPATCHED", ex=86400)
        
        print(f"[Celery] Disparando llamada ID {call_id} con contexto completo guardado en Redis.")
        
        response = requests.post(AMI_CONTROL_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"[Celery] Error de conexión AMI ID {call_id}: {exc}")
        raise self.retry(exc=exc)
    
@celery_app.task(name="sync_call_status")
def sync_call_status():
    """
    Orquestador: Decide si una llamada se completa, se reintenta o espera análisis.
    """
    status_keys = redis_client.keys("call_status:*")
    
    for s_key in status_keys:
        call_id = s_key.split(":")[1]
        asterisk_status = redis_client.get(s_key)
        raw_data = redis_client.get(f"call_data:{call_id}")
        if not raw_data: continue
        
        call_data = json.loads(raw_data)     
        updated_at = datetime.strptime(call_data["updated_at"], "%Y-%m-%d %H:%M:%S")
        timeout_reached = datetime.now() > (updated_at + timedelta(minutes=5))

        if asterisk_status == "COMPLETED":       
            print(f"[Beat] {call_id}: Flujo completado: {asterisk_status}.")
            return finalizar_y_reportar(call_id, call_data, "COMPLETED")
        elif timeout_reached:
            print(f"[Beat] {call_id}: Tiempo limite alcanzado, ultimo estado: {asterisk_status}.")
            return finalizar_y_reportar(call_id, call_data, asterisk_status)
        elif asterisk_status in ["FAILED", "BUSY", "NOANSWER"]:
            print(f"[Beat] {call_id}: Fallo de red/técnico ({asterisk_status}).")
            preparar_reintento_o_fallo(call_id, call_data, s_key)

def finalizar_y_reportar(call_id, call_data, final_status):
    call_data["status"] = final_status
    call_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    redis_client.set(f"call_data:{call_id}", json.dumps(call_data), ex=86400)
    redis_client.delete(f"call_status:{call_id}")
    return send_call_report(call_id, call_data)

def preparar_reintento_o_fallo(call_id, call_data, s_key):
        call_record = call_data["call_record"]
        last_attr = call_record["last_called"]
        
        retry_map = {
            "phone": "alternative_phone",
            "alternative_phone": "alternative_phone_2",
            "alternative_phone_2": None
        }
        
        next_attr = retry_map.get(last_attr)
        next_number = call_data.get(next_attr) if next_attr else None

        was_reported_by_11labs = call_record.get(last_attr, {}).get("failed_reason") is not None

        if next_number:
            print(f"[Beat] Reintentando {call_id} -> {next_attr}: {next_number}")
            call_record[last_attr]["status"] = "FAILED"

            if not was_reported_by_11labs:
                call_record[last_attr]["failed_reason"] = "AST_ISSUE"

            call_record["last_called"] = next_attr
            call_record[next_attr] = {
                "number": next_number,
                "status": "DISPATCHED",
                "failed_reason": None
            }
            call_data["status"] = "RETRYING"
            call_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            redis_client.set(f"call_data:{call_id}", json.dumps(call_data), ex=86400)
            redis_client.set(s_key, "DISPATCHED", ex=86400)

            disparar_llamada_ami.apply_async(
                args=[next_number, call_data["alternative_phone"], call_data.get("alternative_phone_2"), AMI_EXTENSION, call_id],
                countdown=300 
            )
        else:
            print(f"[Beat] {call_id}: Sin más números. Cerrando como fallida.")
            finalizar_y_reportar(call_id, call_data, "FAILED")
            

