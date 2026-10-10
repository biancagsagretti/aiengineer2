from enum import Enum
from pydantic import BaseModel, Field, field_validator

class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"

class AnalisisTecnico(BaseModel):
    tecnologias: list[str] = Field(..., min_length=1,
        description="Tecnologías mencionadas en el texto")
    nivel_de_criticidad: NivelCriticidad = Field(...,
        description="Severidad: baja, media o alta")
    resumen_tecnico: str = Field(...,
        description="Resumen técnico conciso")

    @field_validator("resumen_tecnico")
    @classmethod
    def no_vacio(cls, v):
        if not v.strip():
            raise ValueError("El resumen no puede estar vacío.")
        return v