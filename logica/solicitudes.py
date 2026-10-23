from datetime import date

from bd import basedatos

LIMITE_TIQUETE = 1_500_000  # política de viáticos, sección 3: más de esto requiere al director
LIMITE_COSTO_JEFE = 2_000_000  # nueva política: más de esto requiere al jefe inmediato...
VIGENCIA_COSTO_JEFE = date(2026, 11, 1)  # ...para solicitudes radicadas desde esta fecha

APROBADA = "Aprobada"
RECHAZADA = "Rechazada"
PENDIENTE_DIRECTOR = "Pendiente de director"
PENDIENTE_JEFE = "Pendiente de jefe inmediato"
POR_REVISAR = "Por revisar"


def costo_estimado(noches, valor_noche, valor_tiquete):
    return valor_tiquete + noches * valor_noche


def validar_solicitud(tope_hospedaje, noches, valor_noche, valor_tiquete, fecha=None):
    """Aplica las reglas de reglas_solicitudes.md en orden; la primera que se cumple decide.

    tope_hospedaje es None cuando la ciudad no está en ciudades.csv.
    fecha es el día de radicación (hoy si no se indica); define si rige la regla del jefe inmediato.
    Devuelve (estado, motivo).
    """
    if tope_hospedaje is None:
        return POR_REVISAR, "La ciudad no está en la lista de ciudades con tope de hospedaje"
    if valor_noche > tope_hospedaje:
        return RECHAZADA, f"El valor por noche ({valor_noche}) supera el tope de hospedaje ({tope_hospedaje})"
    if valor_tiquete > LIMITE_TIQUETE:
        return PENDIENTE_DIRECTOR, f"El tiquete ({valor_tiquete}) supera {LIMITE_TIQUETE}: requiere al director"
    costo = costo_estimado(noches, valor_noche, valor_tiquete)
    if (fecha or date.today()) >= VIGENCIA_COSTO_JEFE and costo > LIMITE_COSTO_JEFE:
        return PENDIENTE_JEFE, f"El costo estimado ({costo}) supera {LIMITE_COSTO_JEFE}: requiere al jefe inmediato"
    return APROBADA, "Cumple las reglas"


def _empleado(nombre):
    empleado = basedatos.buscar_empleado(nombre)
    if empleado is None:
        raise ValueError(f"El empleado '{nombre}' no existe en empleados.csv; no se registró nada.")
    return empleado


def registrar_solicitud(nombre_empleado, ciudad, fecha_salida, noches, motivo, valor_noche, valor_tiquete,
                        fecha_radicado=None):
    """Valida y guarda una solicitud. Devuelve radicado, estado, motivo y costo estimado."""
    empleado = _empleado(nombre_empleado)
    fecha_radicado = fecha_radicado or date.today()
    ciudad_bd = basedatos.buscar_ciudad(ciudad)
    estado, motivo_estado = validar_solicitud(
        ciudad_bd["tope_hospedaje"] if ciudad_bd else None, noches, valor_noche, valor_tiquete, fecha_radicado)
    radicado = basedatos.guardar_solicitud(
        empleado["id_empleado"], ciudad_bd["ciudad"] if ciudad_bd else ciudad, fecha_salida,
        noches, motivo, valor_noche, valor_tiquete, estado, fecha_radicado.isoformat())
    return {"radicado": radicado, "estado": estado, "motivo": motivo_estado,
            "costo_estimado": costo_estimado(noches, valor_noche, valor_tiquete)}


def consultar_solicitudes(nombre):
    return basedatos.listar_solicitudes_de_empleado(_empleado(nombre)["id_empleado"])
