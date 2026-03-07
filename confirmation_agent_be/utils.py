import json
import requests

DB_FILE = "db.json"

REPORT_WEBHOOK_URL = "https://eurofirms-i6tza.ondigitalocean.app/api/call-requests/webhook/call-report"
REPORT_AUTH_TOKEN = "435kjo3h4p6h34p56hbñlkn345h6IUGOUBJ"

def leer_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_db(datos):
    with open(DB_FILE, "w") as f:
        json.dump(datos, f, indent=4)

def agregar_llamada(nueva_llamada):
    """
    Agrega un nuevo objeto a la base de datos con el campo email incluido.
    nueva_llamada debe ser un diccionario con la estructura del JSON.
    """
    db = leer_db()
    nuevo_id = db[-1]["id"] + 1 if db else 1
    nueva_llamada["id"] = nuevo_id
    
    db.append(nueva_llamada)
    guardar_db(db)
    return nueva_llamada

def actualizar_llamada(id_llamada, datos_actualizados):
    db = leer_db()
    actualizado = False
    
    for i, llamada in enumerate(db):
        if llamada["id"] == id_llamada:
            db[i] = {**llamada, **datos_actualizados, "id": id_llamada}
            actualizado = True
            break
    
    if actualizado:
        guardar_db(db)
    return actualizado

def eliminar_llamada(id_llamada):
    """
    Elimina el objeto que coincida con el ID proporcionado.
    """
    db = leer_db()
    nueva_db = [llamada for llamada in db if llamada["id"] != id_llamada]
    
    if len(nueva_db) != len(db):
        guardar_db(nueva_db)
        return True
    return False

def get_call_context(phone: str, id_call: int): 
    db = leer_db()
    for llamada in db:
        if str(llamada["id"]) == str(id_call) and llamada["phone"] == phone:
            return {
                "id": llamada.get("id"),
                "username": llamada.get("username"),
                "worker_name": llamada.get("worker_name"),
                "position": llamada.get("position"),
                "work_center": llamada.get("work_center"),
                "address": llamada.get("address"),
                "email": llamada.get("email"),
                "phone": llamada.get("phone"),
                "type": llamada.get("type"),
                "instructions": llamada.get("instructions"),
                "hourly_rate": llamada.get("hourly_rate"),
                "shift_date_raw": llamada.get("shift_date_raw"),
                "shift_start_time": llamada.get("shift_start_time"),
                "shift_end_time": llamada.get("shift_end_time"),
                "status": llamada.get("status"),
                "date": llamada.get("date")
            }
            
    return {}

def _post_report(report_payload):
    """Envia un reporte al webhook externo y retorna la respuesta."""
    headers = {
        "Content-Type": "application/json",
        "Auth-Token": REPORT_AUTH_TOKEN,
    }
    response = requests.post(REPORT_WEBHOOK_URL, json=report_payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def send_partial_call_report(call_id, phone_record):
    """Envia reporte parcial de un numero que fallo. Solo call_id + el registro de ese numero."""
    report_to_send = {
        "call_id": call_id,
        "type": "partial",
        "phone_record": phone_record,
    }

    log_report = json.loads(json.dumps(report_to_send))
    has_audio = False
    analysis = log_report.get("phone_record", {}).get("elevenlabs_analysis", {})
    if analysis and "base64_audio" in analysis:
        audio_val = report_to_send["phone_record"]["elevenlabs_analysis"].get("base64_audio")
        audio_len = len(audio_val) if audio_val else 0
        analysis["base64_audio"] = f"[BASE64_AUDIO — {audio_len} chars]"
        has_audio = True

    print(f"📬 Reporte parcial (call_id={call_id}, audio={'si' if has_audio else 'no'}):")
    print(json.dumps(log_report, indent=2, ensure_ascii=False))

    try:
        resp = _post_report(report_to_send)
        print(f"✅ Reporte parcial enviado OK (call_id={call_id}): {resp}")
    except Exception as e:
        print(f"❌ Error enviando reporte parcial (call_id={call_id}): {e}")


def send_final_call_report(call_id, call_data):
    """Envia reporte final con contexto completo pero solo el registro del ultimo numero."""
    call_record = call_data.get("call_record", {})
    last_called = call_record.get("last_called", "phone")
    last_phone_record = call_record.get(last_called, {})

    report_to_send = {
        "call_id": call_id,
        "type": "final",
        "status": call_data.get("status"),
        "call_context": call_data.get("context", {}),
        "call_record": {
            last_called: last_phone_record,
        },
        "last_updated_at": call_data.get("updated_at"),
    }

    log_report = json.loads(json.dumps(report_to_send))
    has_audio = False
    entry = log_report.get("call_record", {}).get(last_called, {})
    analysis = entry.get("elevenlabs_analysis", {})
    if analysis and "base64_audio" in analysis:
        audio_val = report_to_send["call_record"][last_called]["elevenlabs_analysis"].get("base64_audio")
        audio_len = len(audio_val) if audio_val else 0
        analysis["base64_audio"] = f"[BASE64_AUDIO — {audio_len} chars]"
        has_audio = True

    print(f"📬 Reporte final (call_id={call_id}, status={report_to_send['status']}, audio={'si' if has_audio else 'no'}):")
    print(json.dumps(log_report, indent=2, ensure_ascii=False))

    try:
        resp = _post_report(report_to_send)
        print(f"✅ Reporte final enviado OK (call_id={call_id}): {resp}")
    except Exception as e:
        print(f"❌ Error enviando reporte final (call_id={call_id}): {e}")