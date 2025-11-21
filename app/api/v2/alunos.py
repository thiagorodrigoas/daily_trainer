from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.aluno import Aluno

from app.services.alunos_service import (
    list_alunos,
    get_aluno,
    create_aluno,
    update_aluno,
    delete_aluno,
)
router = APIRouter(prefix="/alunos", tags=["alunos"])


def get_db_cursor():
    with get_cursor() as cursor:
        yield cursor

@router.post("/", response_model=Aluno, status_code=status.HTTP_201_CREATED)
def criar_aluno(aluno: Aluno, cursor=Depends(get_db_cursor)):
    return create_aluno(cursor, aluno)


@router.get("/", response_model=List[Aluno])
def listar_alunos(cursor=Depends(get_db_cursor)):
    return list_alunos(cursor)



@router.get("/{aluno_id}", response_model=Aluno)
def obter_aluno(aluno_id: int, cursor=Depends(get_db_cursor)):
    aluno = get_aluno(cursor, aluno_id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno

@router.put("/{aluno_id}", response_model=Aluno)
def atualizar_aluno(
    aluno_id: int,
    aluno: Aluno,
    cursor=Depends(get_db_cursor),
):
    atualizado = update_aluno(cursor, aluno_id, aluno)
    if not atualizado:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return atualizado


@router.delete("/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_aluno_route(aluno_id: int, cursor=Depends(get_db_cursor)):
    # Poderíamos checar se existia antes, mas mantendo simples por enquanto
    delete_aluno(cursor, aluno_id)
    return
