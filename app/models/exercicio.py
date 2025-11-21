from typing import Optional, Literal
from pydantic import BaseModel, Field


PublicoAlvoType = Literal["masculino", "feminino", "unissex"]


class Exercicio(BaseModel):
    id: Optional[int] = None
    nome: str = Field(..., min_length=1, description="Nome do exercício")
    apelido: Optional[str] = Field(
        None, description="Nome curto/apelido para exibição"
    )
    grupo_muscular: Optional[str] = Field(
        None, description="Ex: Peito, Costas, Pernas, Bíceps"
    )
    descricao: Optional[str] = None
    publico_alvo: PublicoAlvoType = "unissex"
    padrao: bool = False
    series_padrao: int = Field(
        3, ge=1, description="Séries padrão quando usado em treino automático"
    )
    repeticoes_padrao: int = Field(
        10, ge=1, description="Repetições padrão quando usado em treino automático"
    )