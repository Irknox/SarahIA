import os
import requests
from celery import Celery
from dotenv import load_dotenv
from datetime import datetime
from utils import leer_db, guardar_db
import redis

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
    task_reject_on_worker_lost=True,
    broker_transport_options={
        'visibility_timeout': 3600   
    }
)

celery_app.conf.beat_schedule = {
    'revisar-agenda-cada-60-segundos': {
        'task': 'revisar_agenda_y_disparar',
        'schedule': 60.0,
    },
    'sincronizar-estados-redis-db': {
        'task': 'sincronizar_estados_ve_db',
        'schedule': 15.0, 
    },
}

AMI_CONTROL_URL = os.getenv("AMI_URL",)
AMI_TOKEN = os.getenv("AMI_CONTROL_TOKEN")
AMI_EXTENSION=os.getenv('AMI_EXTENSION')

@celery_app.task(name="sincronizar_estados_ve_db")
def sincronizar_estados_ve_db():
    db_actual = leer_db()
    hubo_cambios = False
    for llamada in db_actual:
        if llamada["status"] in ["Agendado", "En curso", "Fallida"]:
            estado_redis = redis_client.get(f"status:{llamada['phone']}")           
            if estado_redis:
                if estado_redis in ["CALLING_AI", "RINGING_HUMAN", "IN_PROGRESS"]:
                    if llamada["status"] != "En curso":
                        llamada["status"] = "En curso"
                        hubo_cambios = True
                elif "FAILED" in estado_redis:
                    if llamada["status"] != "Fallida":
                        llamada["status"] = "Fallida"
                        hubo_cambios = True
    if hubo_cambios:
        guardar_db(db_actual)

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def disparar_llamada_ami(self, user_phone, agent_ext, call_id):
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
        print(f"[Celery] Intentando llamada: {agent_ext} -> {user_phone}!")
        response = requests.post(
            AMI_CONTROL_URL, 
            json=payload, 
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        print(f"[Celery] Éxito: {result}")
        return result
    except requests.exceptions.RequestException as exc:
        print(f"[Celery] Error conectando con AMI Bridge: {exc}")
        raise self.retry(exc=exc)
    
@celery_app.task(name="revisar_agenda_y_disparar")
def revisar_agenda_y_disparar():
    db_actual = leer_db()
    ahora = datetime.now()
    hubo_cambios = False

    for llamada in db_actual:
        if llamada["status"] == "Agendado": 
            fecha_llamada = datetime.strptime(llamada["date"], "%Y-%m-%d %H:%M:%S")
            if fecha_llamada <= ahora or "task_id" not in llamada:
                print(f"[Beat] Rescatando llamada de {llamada['username']}...")
                task = disparar_llamada_ami.delay(llamada["phone"], AMI_EXTENSION, llamada["id"])
                llamada["task_id"] = task.id
                hubo_cambios = True

    if hubo_cambios:
        guardar_db(db_actual)