import csv
import os
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.path.join(CARPETA, "altiplano.db")
RUTA_CSV = os.path.join(os.path.dirname(CARPETA), "kit7")

TABLAS = """
CREATE TABLE IF NOT EXISTS empleados (
    id_empleado TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    area TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ciudades (
    ciudad TEXT PRIMARY KEY,
    grupo TEXT NOT NULL,
    tope_hospedaje INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS solicitudes (
    radicado TEXT PRIMARY KEY,
    fecha_radicado TEXT NOT NULL,
    id_empleado TEXT NOT NULL REFERENCES empleados(id_empleado),
    ciudad TEXT NOT NULL,
    fecha_salida TEXT NOT NULL,
    noches INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    valor_noche INTEGER NOT NULL,
    valor_tiquete INTEGER NOT NULL,
    estado TEXT NOT NULL
);
"""

# archivo CSV -> (tabla, columnas, columnas que son enteros)
CARGAS = {
    "empleados.csv": ("empleados", ["id_empleado", "nombre", "area"], []),
    "ciudades.csv": ("ciudades", ["ciudad", "grupo", "tope_hospedaje"], ["tope_hospedaje"]),
    "solicitudes_historicas.csv": (
        "solicitudes",
        ["radicado", "fecha_radicado", "id_empleado", "ciudad", "fecha_salida", "noches",
         "motivo", "valor_noche", "valor_tiquete", "estado"],
        ["noches", "valor_noche", "valor_tiquete"],
    ),
}


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFD", texto)
    return " ".join("".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower().split())


@contextmanager
def conectar():
    """Abre la base; confirma los cambios al salir y siempre cierra el archivo."""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.create_function("normalizar", 1, normalizar, deterministic=True)
    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def crear_base():
    """Crea las tablas y carga los tres CSV. Se puede repetir sin duplicar filas."""
    with conectar() as conexion:
        conexion.executescript(TABLAS)
        for archivo, (tabla, columnas, enteros) in CARGAS.items():
            with open(os.path.join(RUTA_CSV, archivo), encoding="utf-8-sig", newline="") as f:
                filas = [[int(fila[c]) if c in enteros else fila[c].strip() for c in columnas]
                         for fila in csv.DictReader(f)]
            marcas = ", ".join("?" * len(columnas))
            conexion.executemany(
                f"INSERT OR IGNORE INTO {tabla} ({', '.join(columnas)}) VALUES ({marcas})", filas)


def contar_filas():
    with conectar() as conexion:
        return {t: conexion.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("empleados", "ciudades", "solicitudes")}


def buscar_empleado(nombre):
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT * FROM empleados WHERE normalizar(nombre) = ?", (normalizar(nombre),)).fetchone()
    return dict(fila) if fila else None


def buscar_ciudad(nombre):
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT * FROM ciudades WHERE normalizar(ciudad) = ?", (normalizar(nombre),)).fetchone()
    return dict(fila) if fila else None


def siguiente_radicado(conexion=None):
    if conexion is None:
        with conectar() as propia:
            return siguiente_radicado(propia)
    mayor = conexion.execute("SELECT MAX(CAST(SUBSTR(radicado, 3) AS INTEGER)) FROM solicitudes").fetchone()[0]
    return f"S-{(mayor or 100) + 1}"


def guardar_solicitud(id_empleado, ciudad, fecha_salida, noches, motivo, valor_noche, valor_tiquete,
                      estado, fecha_radicado=None):
    """Guarda la solicitud tal como llega (no aplica reglas) y devuelve su radicado."""
    with conectar() as conexion:
        radicado = siguiente_radicado(conexion)
        conexion.execute(
            "INSERT INTO solicitudes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (radicado, fecha_radicado or date.today().isoformat(), id_empleado, ciudad, fecha_salida,
             int(noches), motivo, int(valor_noche), int(valor_tiquete), estado))
    return radicado


def listar_solicitudes_de_empleado(id_empleado):
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT * FROM solicitudes WHERE id_empleado = ? ORDER BY radicado", (id_empleado,)).fetchall()
    return [dict(f) for f in filas]


if __name__ == "__main__":
    crear_base()
    for tabla, filas in contar_filas().items():
        print(f"{tabla}: {filas} filas")
