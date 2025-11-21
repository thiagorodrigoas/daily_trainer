from typing import Optional, Literal
from pydantic import BaseModel, Field


GeneroType = Literal["masculino", "feminino", "unissex"]


class Aluno(BaseModel):
    id: Optional[int] = None
    nome: str = Field(..., min_length=1)
    genero: GeneroType = "unissex"
    telefone: Optional[str] = None
    turma: Optional[str] = None
    observacoes: Optional[str] = None
