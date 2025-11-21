from typing import Optional
from pydantic import BaseModel, Field


class ExercicioDoTreino(BaseModel):
    id: Optional[int] = None
    treino_id: int = Field(..., description="ID da sessão de treino")
    exercicio_id: int = Field(..., description="ID do exercício realizado")

    series: int = Field(..., ge=1, description="Quantidade de séries")
    repeticoes: int = Field(..., ge=1, description="Repetições por série")
    carga: Optional[float] = Field(
        None, ge=0, description="Carga usada em kg (se aplicável)"
    )
    observacoes: Optional[str] = None
