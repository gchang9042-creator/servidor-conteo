import sqlite3
from flask import Flask, request
import os

app = Flask(__name__)

CLAVE_ADMIN = "admin-mgchs-2026-super-secreta"

conexion = sqlite3.connect("eventos.db", check_same_thread=False)
cursor = conexion.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus TEXT,
        hora TEXT,
        tipo TEXT,
        cliente TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehiculos (
        placa TEXT PRIMARY KEY
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        clave TEXT PRIMARY KEY,
        nombre_cliente TEXT
    )
""")

conexion.commit()


def obtener_cliente_por_clave(clave):
    cursor.execute("SELECT nombre_cliente FROM clientes WHERE clave = ?", (clave,))
    resultado = cursor.fetchone()
    if resultado is None:
        return None
    return resultado[0]


@app.route("/")
def inicio():
    return "¡Hola, soy el servidor!"


@app.route("/evento", methods=["POST"])
def recibir_evento():
    datos = request.get_json()
    clave = datos.get("clave")

    nombre_cliente = obtener_cliente_por_clave(clave)
    if nombre_cliente is None:
        return {"error": "No autorizado"}, 401

    bus = datos["bus"]
    hora = datos["hora"]
    tipo = datos["tipo"]

    cursor.execute("SELECT placa FROM vehiculos WHERE placa = ?", (bus,))
    existe = cursor.fetchone()

    if existe is None:
        return {"error": "Placa no registrada"}, 403

    cursor.execute("INSERT INTO eventos (bus, hora, tipo, cliente) VALUES (?, ?, ?, ?)", (bus, hora, tipo, nombre_cliente))
    conexion.commit()

    return {"mensaje": "Evento guardado correctamente"}


@app.route("/eventos", methods=["GET"])
def obtener_eventos():
    clave = request.args.get("clave")

    nombre_cliente = obtener_cliente_por_clave(clave)
    if nombre_cliente is None:
        return {"error": "No autorizado"}, 401

    cursor.execute("SELECT bus, hora, tipo FROM eventos WHERE cliente = ?", (nombre_cliente,))
    filas = cursor.fetchall()

    lista_eventos = []
    for fila in filas:
        evento = {"bus": fila[0], "hora": fila[1], "tipo": fila[2]}
        lista_eventos.append(evento)

    return {"eventos": lista_eventos}


@app.route("/vehiculos", methods=["GET"])
def obtener_vehiculos():
    if request.args.get("clave") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    cursor.execute("SELECT placa FROM vehiculos")
    filas = cursor.fetchall()

    lista_placas = []
    for fila in filas:
        lista_placas.append(fila[0])

    return {"vehiculos": lista_placas}


@app.route("/vehiculo", methods=["POST"])
def agregar_vehiculo():
    datos = request.get_json()

    if datos.get("clave") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    placa = datos["placa"].strip().upper()

    cursor.execute("INSERT OR IGNORE INTO vehiculos (placa) VALUES (?)", (placa,))
    conexion.commit()

    return {"mensaje": "Vehiculo agregado correctamente"}


@app.route("/vehiculo", methods=["DELETE"])
def eliminar_vehiculo():
    datos = request.get_json()

    if datos.get("clave") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    placa = datos["placa"].strip().upper()

    cursor.execute("DELETE FROM vehiculos WHERE placa = ?", (placa,))
    conexion.commit()

    return {"mensaje": "Vehiculo eliminado correctamente"}


@app.route("/clientes", methods=["GET"])
def obtener_clientes():
    if request.args.get("clave") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    cursor.execute("SELECT clave, nombre_cliente FROM clientes")
    filas = cursor.fetchall()

    lista_clientes = []
    for fila in filas:
        cliente = {"clave": fila[0], "nombre_cliente": fila[1]}
        lista_clientes.append(cliente)

    return {"clientes": lista_clientes}


@app.route("/cliente", methods=["POST"])
def agregar_cliente():
    datos = request.get_json()

    if datos.get("clave_admin") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    clave_nueva = datos["clave_cliente"].strip()
    nombre_cliente = datos["nombre_cliente"].strip()

    cursor.execute("INSERT OR IGNORE INTO clientes (clave, nombre_cliente) VALUES (?, ?)", (clave_nueva, nombre_cliente))
    conexion.commit()

    return {"mensaje": "Cliente agregado correctamente"}


@app.route("/cliente", methods=["DELETE"])
def eliminar_cliente():
    datos = request.get_json()

    if datos.get("clave_admin") != CLAVE_ADMIN:
        return {"error": "No autorizado"}, 401

    clave_eliminar = datos["clave_cliente"].strip()

    cursor.execute("DELETE FROM clientes WHERE clave = ?", (clave_eliminar,))
    conexion.commit()

    return {"mensaje": "Cliente eliminado correctamente"}


app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))