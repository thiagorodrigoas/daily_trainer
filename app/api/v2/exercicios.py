from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.exercicio import Exercicio

from app.services.exercicios_service import (
    list_exercicios,
    get_exercicio,
    create_exercicio,
    update_exercicio,
    delete_exercicio,
)


router = APIRouter(prefix="/exercicios", tags=["exercicios"])


def get_db_cursor():
    with get_cursor() as cursor:
        yield cursor


@router.post(
    "/", response_model=Exercicio, status_code=status.HTTP_201_CREATED
)
def criar_exercicio_route(
    exercicio: Exercicio,
    cursor=Depends(get_db_cursor),
):
    return create_exercicio(cursor, exercicio)

@router.get("/", response_model=List[Exercicio])
def listar_exercicios_route(
    genero: Optional[str] = None,
    cursor=Depends(get_db_cursor),
):
    try:
        return list_exercicios(cursor, genero=genero)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Gênero inválido. Use 'masculino', 'feminino' ou 'unissex'.",
        )

@router.get("/{exercicio_id}", response_model=Exercicio)
def obter_exercicio_route(
    exercicio_id: int,
    cursor=Depends(get_db_cursor),
):
    exercicio = get_exercicio(cursor, exercicio_id)
    if not exercicio:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    return exercicio

@router.put("/{exercicio_id}", response_model=Exercicio)
def atualizar_exercicio_route(
    exercicio_id: int,
    exercicio: Exercicio,
    cursor=Depends(get_db_cursor),
):
    atualizado = update_exercicio(cursor, exercicio_id, exercicio)
    if not atualizado:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    return atualizado

@router.delete("/{exercicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_exercicio_route(
    exercicio_id: int,
    cursor=Depends(get_db_cursor),
):
    ok = delete_exercicio(cursor, exercicio_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    return
