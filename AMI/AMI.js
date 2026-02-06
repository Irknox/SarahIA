require("dotenv").config();
const express = require("express");
const AmiClient = require("asterisk-ami-client");

const {
  AMI_CONTROL_TOKEN,
  AMI_HOST = "127.0.0.1",
  AMI_PORT = 5038,
  AMI_USER,
  AMI_PASS,
  AMI_TRANSFER_CONTEXT,
} = process.env;

if (!AMI_CONTROL_TOKEN) throw new Error("Falta AMI_CONTROL_TOKEN");
if (!AMI_USER || !AMI_PASS) throw new Error("Faltan AMI_USER/AMI_PASS");

const app = express();
app.use(express.json());

const ami = new AmiClient();

ami
  .connect(AMI_USER, AMI_PASS, { host: AMI_HOST, port: AMI_PORT })
  .then(() => console.log(`[AMI] Conectado exitosamente a ${AMI_HOST}`))
  .catch((err) => console.error("[AMI] Error de conexión inicial:", err));

app.post("/originate", async (req, res) => {
  try {
    const token = req.header("x-ari-control-token") || "";
    if (token !== AMI_CONTROL_TOKEN) {
      console.warn("[AMI] Intento de acceso no autorizado");
      return res.status(403).json({ error: "Unauthorized" });
    }
    const { user_phone, agent_ext, call_id } = req.body || {};

    if (!user_phone || !agent_ext || !call_id) {
      return res.status(400).json({
        error: "Faltan parámetros: user_phone, agent_ext o call_id",
      });
    }
    const channelTarget = `Local/${agent_ext}@from-internal-custom`;

    console.log(
      `[AMI] Disparando Originate: ${channelTarget} -> ${user_phone}`,
    );

    const actionData = {
      Action: "Originate",
      Channel: `PJSIP/${user_phone}@ext-remote`,
      Context: "from-internal-custom",
      Exten: "7777",
      Priority: 1,
      Async: "true",
      Variable: `DESTINO_HUMANO=${user_phone},__X_CALL_ID=${call_id},__X_CALLER_ID=${user_phone}`,
    };

    const response = await ami.action(actionData);

    console.log("[AMI] Comando aceptado por Asterisk para ID:", call_id);

    return res.json({
      status: "success",
      message: "Llamada lanzada correctamente",
      asterisk_ref: response.ActionID || "pending",
    });
  } catch (error) {
    console.error("[AMI] Error crítico en originate:", error);
    return res.status(500).json({
      status: "error",
      message: "Asterisk rechazó el comando o está desconectado",
      detail: error.message,
    });
  }
});

const PORT = 8282;
app.listen(PORT, () => {
  console.log(`[AMI Bridge] Escuchando en puerto ${PORT}`);
});
