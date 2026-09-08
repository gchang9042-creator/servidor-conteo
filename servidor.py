import sqlite3
from flask import Flask, request
import os

app = Flask(__name__)

CLAVE_SECRETA = "unidades-moviles-2620-mgchs"

conexion = sqlite3.connect("eventos.db", check_same_thread=False)
cursor = conexion.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus TEXT,
        hora TEXT,
        tipo TEXT
    )
""")
conexion.commit()

@app.route("/")
def inicio():
    return "¡Hola, soy el servidor!"

@app.route("/evento", methods=["POST"])
def recibir_evento():
    datos = request.get_json()

    if datos.get("clave") != CLAVE_SECRETA:
        return {"error": "No autorizado"}, 401

    print("Evento recibido:", datos)

    bus = datos["bus"]
    hora = datos["hora"]
    tipo = datos["tipo"]

    cursor.execute("INSERT INTO eventos (bus, hora, tipo) VALUES (?, ?, ?)", (bus, hora, tipo))
    conexion.commit()

    return {"mensaje": "Evento guardado correctamente"}

@app.route("/eventos", methods=["GET"])
def obtener_eventos():
    clave_recibida = request.args.get("clave")

    if clave_recibida != CLAVE_SECRETA:
        return {"error": "No autorizado"}, 401

    cursor.execute("SELECT bus, hora, tipo FROM eventos")
    filas = cursor.fetchall()

    lista_eventos = []
    for fila in filas:
        evento = {"bus": fila[0], "hora": fila[1], "tipo": fila[2]}
        lista_eventos.append(evento)

    return {"eventos": lista_eventos}

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))