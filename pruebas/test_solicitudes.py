from datetime import date

import pytest

from bd import basedatos
from logica import solicitudes
from logica.solicitudes import (APROBADA, PENDIENTE_DIRECTOR, PENDIENTE_JEFE, POR_REVISAR,
                                RECHAZADA, validar_solicitud)

TOPES = {"Bogotá": 320000, "Medellín": 320000, "Cartagena": 320000,
         "Barranquilla": 240000, "Bucaramanga": 240000}

# (caso, ciudad, noches, valor_noche, valor_tiquete, estado esperado)
CASOS = [
    ("C1", "Medellín", 2, 320000, 1360000, APROBADA),            # hotel igual al tope cumple; tiquete bajo el límite
    ("C2", "Bucaramanga", 3, 262000, 390000, RECHAZADA),         # 262.000 > tope 240.000
    ("C3", "Cartagena", 1, 300000, 1500000, APROBADA),           # tiquete igual al límite cumple
    ("C4", "Bogotá", 2, 250000, 1620000, PENDIENTE_DIRECTOR),    # hotel ok, tiquete > 1.500.000
    ("C5", "Miami", 3, 280000, 2100000, POR_REVISAR),            # sin tope: la regla 1 decide antes que el tiquete
    ("C6", "Barranquilla", 4, 240000, 1100000, APROBADA),        # hotel igual al tope cumple
]


ANTES_DE_LA_NUEVA_REGLA = date(2026, 10, 31)
DESDE_LA_NUEVA_REGLA = date(2026, 11, 1)


@pytest.mark.parametrize("caso, ciudad, noches, valor_noche, valor_tiquete, esperado", CASOS)
def test_validar_solicitud(caso, ciudad, noches, valor_noche, valor_tiquete, esperado):
    estado, motivo = validar_solicitud(TOPES.get(ciudad), noches, valor_noche, valor_tiquete,
                                       ANTES_DE_LA_NUEVA_REGLA)
    assert estado == esperado
    assert motivo


# Desde el 1 de noviembre de 2026: costo estimado > 2.000.000 requiere al jefe inmediato.
# Solo C6 cambia (4 x 240.000 + 1.100.000 = 2.060.000). C1 cuesta exactamente 2.000.000 y no cambia;
# C4 cuesta 2.120.000 pero ya requiere al director, y C2 y C5 se deciden por reglas anteriores.
CASOS_NUEVA_REGLA = [
    {**dict(zip(("caso", "ciudad", "noches", "valor_noche", "valor_tiquete", "esperado"), c))}
    for c in CASOS
]
CASOS_NUEVA_REGLA[5]["esperado"] = PENDIENTE_JEFE


@pytest.mark.parametrize("c", CASOS_NUEVA_REGLA, ids=lambda c: c["caso"])
def test_regla_costo_jefe_desde_noviembre(c):
    estado, motivo = validar_solicitud(TOPES.get(c["ciudad"]), c["noches"], c["valor_noche"],
                                       c["valor_tiquete"], DESDE_LA_NUEVA_REGLA)
    assert estado == c["esperado"]
    assert motivo


@pytest.fixture
def base_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(basedatos, "RUTA_BD", str(tmp_path / "prueba.db"))
    basedatos.crear_base()


def test_registrar_guarda_con_el_siguiente_radicado(base_temporal):
    resultado = solicitudes.registrar_solicitud(
        "natalia guzman", "cartagena", "2026-11-03", 2, "Feria comercial", 310000, 690000)
    assert resultado["radicado"] == "S-141"
    assert resultado["estado"] == APROBADA
    assert resultado["costo_estimado"] == 1310000
    assert solicitudes.consultar_solicitudes("Natalia Guzmán")[-1]["radicado"] == "S-141"


def test_empleado_inexistente_no_registra_nada(base_temporal):
    with pytest.raises(ValueError, match="no existe"):
        solicitudes.registrar_solicitud("Nadie Aquí", "Bogotá", "2026-11-03", 1, "x", 100000, 100000)
    assert basedatos.contar_filas()["solicitudes"] == 40
