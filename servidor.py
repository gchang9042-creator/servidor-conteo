# ==========================================================
#  servidor.py — Servidor central del sistema de conteo
#  Guarda clientes, vehículos y eventos de entrada/salida
# ==========================================================

import os
import sqlite3
from datetime import datetime

from flask import Flask, request, jsonify

app = Flask(__name__)

ARCHIVO_BD = "conteo.db"

# La clave de administrador NO se escribe aquí.
# Se configura en Render: Environment -> CLAVE_ADMIN
CLAVE_ADMIN = os.environ.get("CLAVE_ADMIN")


# ---------- BASE DE DATOS ----------

def conectar():
    conexion = sqlite3.connect(ARCHIVO_BD)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():
    conexion = conectar()
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            clave TEXT PRIMARY KEY,
            nombre_cliente TEXT UNIQUE NOT NULL
        )
    """)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos (
            placa TEXT PRIMARY KEY,
            cliente TEXT NOT NULL
        )
    """)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
    """)
    conexion.commit()
    conexion.close()


# ---------- FUNCIONES DE AYUDA ----------

def es_admin(clave):
    return CLAVE_ADMIN is not None and clave == CLAVE_ADMIN


def leer_json():
    datos = request.get_json(silent=True)
    if datos is None:
        return {}
    return datos


def buscar_cliente_por_clave(clave):
    conexion = conectar()
    fila = conexion.execute(
        "SELECT * FROM clientes WHERE clave = ?", (clave,)
    ).fetchone()
    conexion.close()
    return fila


# ---------- PÁGINA DE PRUEBA ----------

@app.route("/")
def inicio():
    return jsonify({"mensaje": "Servidor de conteo funcionando"})


# ---------- CLIENTES (solo administrador) ----------

@app.route("/clientes", methods=["GET"])
def listar_clientes():
    if not es_admin(request.args.get("clave")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    conexion = conectar()
    filas = conexion.execute(
        "SELECT nombre_cliente, clave FROM clientes ORDER BY nombre_cliente"
    ).fetchall()
    conexion.close()

    lista = []
    for fila in filas:
        lista.append({"nombre_cliente": fila["nombre_cliente"], "clave": fila["clave"]})
    return jsonify({"clientes": lista})


@app.route("/cliente", methods=["POST"])
def agregar_cliente():
    datos = leer_json()
    if not es_admin(datos.get("clave_admin")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    nombre = str(datos.get("nombre_cliente", "")).strip()
    clave = str(datos.get("clave_cliente", "")).strip()
    if nombre == "" or clave == "":
        return jsonify({"mensaje": "Faltan el nombre o la clave"}), 400

    conexion = conectar()
    try:
        conexion.execute(
            "INSERT INTO clientes (clave, nombre_cliente) VALUES (?, ?)",
            (clave, nombre),
        )
        conexion.commit()
        mensaje = "Cliente agregado: " + nombre
        codigo = 200
    except sqlite3.IntegrityError:
        mensaje = "Ya existe un cliente con ese nombre o esa clave"
        codigo = 400
    conexion.close()
    return jsonify({"mensaje": mensaje}), codigo


@app.route("/cliente/clave", methods=["POST"])
def cambiar_clave_cliente():
    datos = leer_json()
    if not es_admin(datos.get("clave_admin")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    nombre = str(datos.get("nombre_cliente", "")).strip()
    clave_nueva = str(datos.get("clave_nueva", "")).strip()
    if nombre == "" or clave_nueva == "":
        return jsonify({"mensaje": "Faltan el nombre o la clave nueva"}), 400

    conexion = conectar()
    try:
        cursor = conexion.execute(
            "UPDATE clientes SET clave = ? WHERE nombre_cliente = ?",
            (clave_nueva, nombre),
        )
        conexion.commit()
        if cursor.rowcount == 0:
            mensaje = "No existe ese cliente"
            codigo = 404
        else:
            mensaje = "Clave actualizada para " + nombre
            codigo = 200
    except sqlite3.IntegrityError:
        mensaje = "Esa clave ya la usa otro cliente"
        codigo = 400
    conexion.close()
    return jsonify({"mensaje": mensaje}), codigo


@app.route("/cliente", methods=["DELETE"])
def eliminar_cliente():
    datos = leer_json()
    if not es_admin(datos.get("clave_admin")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    clave = str(datos.get("clave_cliente", "")).strip()
    cliente = buscar_cliente_por_clave(clave)
    if cliente is None:
        return jsonify({"mensaje": "No existe ese cliente"}), 404

    # Al borrar un cliente también se borran sus vehículos
    conexion = conectar()
    conexion.execute("DELETE FROM vehiculos WHERE cliente = ?", (cliente["nombre_cliente"],))
    conexion.execute("DELETE FROM clientes WHERE clave = ?", (clave,))
    conexion.commit()
    conexion.close()
    return jsonify({"mensaje": "Cliente eliminado: " + cliente["nombre_cliente"]})


# ---------- VEHÍCULOS (solo administrador) ----------

@app.route("/vehiculos", methods=["GET"])
def listar_vehiculos():
    if not es_admin(request.args.get("clave")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    conexion = conectar()
    filas = conexion.execute(
        "SELECT placa, cliente FROM vehiculos ORDER BY cliente, placa"
    ).fetchall()
    conexion.close()

    lista = []
    for fila in filas:
        lista.append({"placa": fila["placa"], "cliente": fila["cliente"]})
    return jsonify({"vehiculos": lista})


@app.route("/vehiculo", methods=["POST"])
def agregar_vehiculo():
    datos = leer_json()
    if not es_admin(datos.get("clave")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    placa = str(datos.get("placa", "")).strip().upper()
    cliente = str(datos.get("cliente", "")).strip()
    if placa == "" or cliente == "":
        return jsonify({"mensaje": "Faltan la placa o el cliente"}), 400

    conexion = conectar()
    existe = conexion.execute(
        "SELECT 1 FROM clientes WHERE nombre_cliente = ?", (cliente,)
    ).fetchone()
    if existe is None:
        conexion.close()
        return jsonify({"mensaje": "Ese cliente no existe"}), 404

    try:
        conexion.execute(
            "INSERT INTO vehiculos (placa, cliente) VALUES (?, ?)", (placa, cliente)
        )
        conexion.commit()
        mensaje = "Vehículo " + placa + " asignado a " + cliente
        codigo = 200
    except sqlite3.IntegrityError:
        mensaje = "Esa placa ya está registrada"
        codigo = 400
    conexion.close()
    return jsonify({"mensaje": mensaje}), codigo


@app.route("/vehiculo", methods=["DELETE"])
def eliminar_vehiculo():
    datos = leer_json()
    if not es_admin(datos.get("clave")):
        return jsonify({"mensaje": "Clave de administrador incorrecta"}), 403

    placa = str(datos.get("placa", "")).strip().upper()
    conexion = conectar()
    cursor = conexion.execute("DELETE FROM vehiculos WHERE placa = ?", (placa,))
    conexion.commit()
    conexion.close()

    if cursor.rowcount == 0:
        return jsonify({"mensaje": "No existe esa placa"}), 404
    return jsonify({"mensaje": "Vehículo eliminado: " + placa})


# ---------- EVENTOS (los envía el programa de conteo de cada bus) ----------

@app.route("/evento", methods=["POST"])
def registrar_evento():
    datos = leer_json()
    cliente = buscar_cliente_por_clave(str(datos.get("clave", "")).strip())
    if cliente is None:
        return jsonify({"mensaje": "Clave de cliente incorrecta"}), 403

    placa = str(datos.get("placa", "")).strip().upper()
    tipo = str(datos.get("tipo", "")).strip().lower()
    fecha = datos.get("fecha") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if tipo not in ("entrada", "salida"):
        return jsonify({"mensaje": "El tipo debe ser 'entrada' o 'salida'"}), 400

    conexion = conectar()
    vehiculo = conexion.execute(
        "SELECT 1 FROM vehiculos WHERE placa = ? AND cliente = ?",
        (placa, cliente["nombre_cliente"]),
    ).fetchone()
    if vehiculo is None:
        conexion.close()
        return jsonify({"mensaje": "Ese vehículo no está autorizado para este cliente"}), 403

    conexion.execute(
        "INSERT INTO eventos (placa, tipo, fecha) VALUES (?, ?, ?)", (placa, tipo, fecha)
    )
    conexion.commit()
    conexion.close()
    return jsonify({"mensaje": "Evento guardado"})


@app.route("/eventos", methods=["GET"])
def listar_eventos():
    clave = request.args.get("clave", "")
    placa = request.args.get("placa", "").strip().upper()

    conexion = conectar()
    if es_admin(clave):
        consulta = "SELECT e.placa, e.tipo, e.fecha, v.cliente FROM eventos e LEFT JOIN vehiculos v ON e.placa = v.placa"
        parametros = []
        if placa != "":
            consulta += " WHERE e.placa = ?"
            parametros.append(placa)
    else:
        cliente = buscar_cliente_por_clave(clave)
        if cliente is None:
            conexion.close()
            return jsonify({"mensaje": "Clave incorrecta"}), 403
        consulta = "SELECT e.placa, e.tipo, e.fecha, v.cliente FROM eventos e JOIN vehiculos v ON e.placa = v.placa WHERE v.cliente = ?"
        parametros = [cliente["nombre_cliente"]]
        if placa != "":
            consulta += " AND e.placa = ?"
            parametros.append(placa)

    consulta += " ORDER BY e.fecha DESC LIMIT 500"
    filas = conexion.execute(consulta, parametros).fetchall()
    conexion.close()

    lista = []
    for fila in filas:
        lista.append({
            "placa": fila["placa"],
            "tipo": fila["tipo"],
            "fecha": fila["fecha"],
            "cliente": fila["cliente"],
        })
    return jsonify({"eventos": lista})


# ---------- ARRANQUE ----------

crear_tablas()

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)