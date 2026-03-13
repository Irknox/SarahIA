import asyncio
import requests
import os

AMI_CONTROL_TOKEN = os.getenv("AMI_CONTROL_TOKEN")
AMI_CONTROL_URL = os.getenv("AMI_CONTROL_URL")

def Make_outbound_ai_call_tool():
    """
    Genera la función para disparar llamadas salientes automáticas 
    conectando ElevenLabs con un usuario final.
    """
    async def trigger_outbound_call(user_phone: str, agent_id: str = "9998"):
        """
        user_phone: Número del cliente (ej: +50688888888)
        agent_id: La extensión o ID del agente en ElevenLabs (por defecto 9998)
        """
        if not user_phone:
            print("Missing User Phone")
            return {"status": "error", "reason": "missing_user_phone"}
        if not AMI_CONTROL_TOKEN:
            print("Falta AMI_CONTROL_TOKEN en ENV")
            return {"status": "error", "reason": "missing_control_token"}
        print(f"Iniciando llamada de IA 🤖 hacia {user_phone} usando agente {agent_id}")
        url = AMI_CONTROL_URL.rstrip("/") + "/originate"
        payload = {
            "user_phone": user_phone,
            "agent_ext": agent_id,
            "mode": "ai_outbound"
        }
        headers = {
            "x-ari-control-token": AMI_CONTROL_TOKEN,
            "Content-Type": "application/json",
        }
        def _do_request():
            return requests.post(url, headers=headers, json=payload, timeout=10)
        try:
            resp = await asyncio.to_thread(_do_request)
            
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            if resp.ok:
                print(f"Solicitud de Originate aceptada por el bridge, respuesta: {data}")
                return {
                    "status": "success", 
                    "message": "Call triggered", 
                    "ami_data": data
                }
            else:
                print(f"Error en respuesta del bridge AMI: {data}")
                return {
                    "status": "error", 
                    "http_status": resp.status_code, 
                    "response": data
                }

        except Exception as e:
            print(f"Error al contactar con el microservicio AMI: {e}")
            return {
                "status": "error", 
                "reason": "request_failed", 
                "detail": str(e)
            }

    return trigger_outbound_call