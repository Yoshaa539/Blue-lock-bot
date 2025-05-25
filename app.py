from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
ADMIN_NUMBER = "+52481050323"

# Crear base de datos si no existe
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    fecha TEXT,
                    gol INTEGER,
                    atajada INTEGER,
                    robadas INTEGER,
                    asistencias INTEGER,
                    mvp INTEGER,
                    rechaces INTEGER
                )''')
    conn.commit()
    conn.close()

init_db()

def calcular_puntos(fila):
    return (
        fila["gol"] * 100 +
        fila["atajadas"] * 50 +
        fila["robadas"] * 60 +
        fila["asistencias"] * 30 +
        fila["mvp"] * 200 +
        fila["rechaces"] * 70
    )

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    body = request.form.get("Body", "").strip().lower()
    from_number = request.form.get("From", "")
    resp = MessagingResponse()

    if body.startswith("/registro"):
        lineas = body.splitlines()[1:]  # Ignorar "/registro"
        datos = {"gol": 0, "atajadas": 0, "robadas": 0, "asistencias": 0, "mvp": 0, "rechaces": 0}
        nombre = None

        for linea in lineas:
            if ":" in linea:
                k, v = linea.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "jugador":
                    nombre = v
                elif k in datos:
                    datos[k] = int(v)

        if not nombre:
            resp.message("Falta el nombre del jugador.")
            return str(resp)

        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute('''INSERT INTO stats (nombre, fecha, gol, atajada, robadas, asistencias, mvp, rechaces)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (nombre, hoy, datos["gol"], datos["atajadas"], datos["robadas"],
                   datos["asistencias"], datos["mvp"], datos["rechaces"]))
        conn.commit()
        conn.close()
        resp.message(f"{nombre} registrado correctamente para {hoy}.")
        return str(resp)

    elif body.startswith("/ranking"):
        if not from_number.endswith(ADMIN_NUMBER.replace("+", "")):
            resp.message("Comando no autorizado.")
            return str(resp)

        partes = body.split()
        if len(partes) == 2:
            fecha = partes[1]
        else:
            fecha = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        conn = sqlite3.connect("data.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM stats WHERE fecha = ?", (fecha,))
        filas = c.fetchall()
        conn.close()

        if not filas:
            resp.message(f"No hay datos para {fecha}.")
            return str(resp)

        puntos_por_jugador = {}
        for fila in filas:
            nombre = fila["nombre"]
            puntos = calcular_puntos(fila)
            puntos_por_jugador[nombre] = puntos_por_jugador.get(nombre, 0) + puntos

        ranking = sorted(puntos_por_jugador.items(), key=lambda x: x[1], reverse=True)
        mensaje = f"Ranking del {fecha}:

"
        for i, (nombre, puntos) in enumerate(ranking, start=1):
            mensaje += f"{i}. {nombre} - {puntos} pts
"

        resp.message(mensaje.strip())
        return str(resp)

    else:
        resp.message("Comandos:
/registro
/ranking
/ranking YYYY-MM-DD")
        return str(resp)

if __name__ == "__main__":
    app.run(debug=True)