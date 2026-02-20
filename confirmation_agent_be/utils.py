import json

DB_FILE = "db.json"

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