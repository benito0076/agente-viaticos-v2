from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from bd import basedatos
from logica import solicitudes


@asynccontextmanager
async def inicio(_):
    basedatos.crear_base()  # abre la base (la crea y carga los CSV si hace falta; no duplica filas)
    yield


app = FastAPI(title="API de viáticos - Altiplano S.A.S.", lifespan=inicio)


class SolicitudNueva(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "empleado": "Natalia Guzmán",
        "ciudad": "Medellín",
        "fecha_salida": "2026-11-17",
        "noches": 1,
        "motivo": "Auditoría de bodega",
        "valor_noche": 280000,
        "valor_tiquete": 450000,
    }})

    empleado: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    fecha_salida: date
    noches: int = Field(ge=0)
    motivo: str = Field(min_length=1)
    valor_noche: int = Field(ge=0)
    valor_tiquete: int = Field(ge=0)


class Resultado(BaseModel):
    radicado: str
    estado: str
    motivo: str


@app.get("/solicitudes")
def consultar(empleado: str = Query(min_length=1, description="Nombre del empleado")):
    try:
        return solicitudes.consultar_solicitudes(empleado)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.post("/solicitudes", response_model=Resultado)
def registrar(solicitud: SolicitudNueva):
    try:
        return solicitudes.registrar_solicitud(
            solicitud.empleado, solicitud.ciudad, solicitud.fecha_salida.isoformat(), solicitud.noches,
            solicitud.motivo, solicitud.valor_noche, solicitud.valor_tiquete)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
