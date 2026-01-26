import os
import requests
from celery import Celery
from dotenv import load_dotenv
from datetime import datetime
from utils import leer_db, guardar_db

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

celery_app = Celery(
    "Sarah_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC', 
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    'revisar-agenda-cada-60-segundos': {
        'task': 'revisar_agenda_y_disparar',
        'schedule': 60.0,
    },
}

AMI_CONTROL_URL = os.getenv("AMI_CONTROL_URL",)
AMI_TOKEN = os.getenv("AMI_CONTROL_TOKEN")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def disparar_llamada_ami(self, user_phone, agent_ext):
    payload = {
        "user_phone": user_phone,
        "agent_ext": agent_ext
    }
    headers = {
        "x-ari-control-token": AMI_TOKEN,
        "Content-Type": "application/json"
    }
    try:
        print(f"[Celery] Intentando llamada: {agent_ext} -> {user_phone}")
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
    ahora = datetime.utcnow()
    hubo_cambios = False

    print(f"[Beat] Revisando agenda a las {ahora}...")

    for llamada in db_actual:
        if llamada["status"] == "scheduled" and llamada["scheduled"] != "NOW":
            fecha_llamada = datetime.strptime(llamada["scheduled"], "%Y-%m-%d %H:%M:%S")
            
            if fecha_llamada <= ahora:
                print(f"[Beat] Disparando llamada pendiente para {llamada['phone']}...")
                llamada["status"] = "completed"
                disparar_llamada_ami.delay(llamada["phone"], llamada["agent_ext"])
                hubo_cambios = True

    if hubo_cambios:
        guardar_db(db_actual)