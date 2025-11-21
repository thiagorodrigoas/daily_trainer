from typing import Optional, Literal, List
from datetime import date
from pydantic import BaseModel, Field
from app.models.exercicio_do_treino import ExercicioDoTreino

class Treino(BaseModel):
    id: Optional[int] = None
    aluno_id: int = Field(..., description="ID do aluno que realizou o treino")
    data: date = Field(..., description="Data da sessão de treino")
    observacoes: Optional[str] = None


PerfilType = Literal["leve", "moderado", "intenso"]


class GerarTreinoPorMusculosRequest(BaseModel):
    aluno_id: int
    data: date
    observacoes: Optional[str] = None
    grupos_musculares: List[str] = Field(
        ..., description="Lista de grupos musculares, ex: ['biceps', 'peito']"
    )
    perfil: PerfilType = Field(
        "moderado",
        description="Perfil de intensidade: leve, moderado, intenso",
    )


class TreinoGerado(BaseModel):
    treino: Treino
    exercicios: List[ExercicioDoTreino]

class ReordenarRequest(BaseModel):
    ordem: List[int]  # lista de IDs da tabela exercicios_do_treino NA NOVA ORDEM
