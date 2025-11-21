from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.aluno import Aluno

router = APIRouter(prefix="/alunos", tags=["alunos"])


def get_db_cursor():
    with get_cursor() as cursor:
        yield cursor


@router.post("/", response_model=Aluno, status_code=status.HTTP_201_CREATED)
def criar_aluno(aluno: Aluno, cursor=Depends(get_db_cursor)):
    cursor.execute(
        """
        INSERT INTO alunos (id, nome, genero, telefone, observacoes)
        VALUES (nextval('alunos_seq'), ?, ?, ?, ?)
        RETURNING id;
        """,
        [aluno.nome, aluno.genero, aluno.telefone, aluno.observacoes],
    )
    new_id = cursor.fetchone()[0]
    return Aluno(
        id=new_id,
        **aluno.model_dump(exclude={"id"}),
    )


@router.get("/", response_model=List[Aluno])
def listar_alunos(cursor=Depends(get_db_cursor)):
    cursor.execute(
        """
        SELECT id, nome, genero, telefone, observacoes
        FROM alunos
        ORDER BY id;
        """
    )
    rows = cursor.fetchall()
    return [
        Aluno(
            id=row[0],
            nome=row[1],
            genero=row[2],
            telefone=row[3],
            observacoes=row[4],
        )
        for row in rows
    ]


@router.get("/{aluno_id}", response_model=Aluno)
def obter_aluno(aluno_id: int, cursor=Depends(get_db_cursor)):
    cursor.execute(
        """
        SELECT id, nome, genero, telefone, observacoes
        FROM alunos
        WHERE id = ?;
        """,
        [aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    return Aluno(
        id=row[0],
        nome=row[1],
        genero=row[2],
        telefone=row[3],
        observacoes=row[4],
    )

@router.put("/{aluno_id}", response_model=Aluno)
def atualizar_aluno(
    aluno_id: int,
    aluno: Aluno,
    cursor=Depends(get_db_cursor),
):
    """
    Atualiza todos os dados de um aluno.
    """

    # Verifica se existe
    cursor.execute(
        "SELECT id FROM alunos WHERE id = ?;",
        [aluno_id],
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    cursor.execute(
        """
        UPDATE alunos
        SET nome = ?, genero = ?, telefone = ?, observacoes = ?
        WHERE id = ?;
        """,
        [
            aluno.nome,
            aluno.genero,
            aluno.telefone,
            aluno.observacoes,
            aluno_id,
        ],
    )

    return Aluno(
        id=aluno_id,
        **aluno.model_dump(exclude={"id"}),
    )

@router.delete("/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_aluno(aluno_id: int, cursor=Depends(get_db_cursor)):
    cursor.execute(
        "DELETE FROM exercicios_do_treino WHERE treino_id IN (SELECT id FROM treinos WHERE aluno_id = ?);",
        [aluno_id],
    )
    cursor.execute("DELETE FROM treinos WHERE aluno_id = ?;", [aluno_id])
    cursor.execute("DELETE FROM alunos WHERE id = ?;", [aluno_id])
    return
