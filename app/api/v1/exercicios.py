from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.exercicio import Exercicio

router = APIRouter(prefix="/exercicios", tags=["exercicios"])


def get_db_cursor():
    with get_cursor() as cursor:
        yield cursor


@router.post(
    "/", response_model=Exercicio, status_code=status.HTTP_201_CREATED
)
def criar_exercicio(exercicio: Exercicio, cursor=Depends(get_db_cursor)):
    cursor.execute(
        """
        INSERT INTO exercicios (id, nome, apelido, grupo_muscular, descricao, publico_alvo, padrao, series_padrao, repeticoes_padrao)
        VALUES (nextval('exercicios_seq'), ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        [
            exercicio.nome,
            exercicio.apelido,
            exercicio.grupo_muscular,
            exercicio.descricao,
            exercicio.publico_alvo,
            exercicio.padrao,
            exercicio.series_padrao,
            exercicio.repeticoes_padrao

        ],
    )
    new_id = cursor.fetchone()[0]
    return Exercicio(
        id=new_id,
        **exercicio.model_dump(exclude={"id"}),
    )


@router.get("/", response_model=List[Exercicio])
def listar_exercicios(
    genero: Optional[str] = None,
    cursor=Depends(get_db_cursor),
):
    """
    Lista exercícios.
    Se 'genero' for informado (masculino/feminino/unissex), aplica filtro:
      - masculino/feminino: exercícios daquele gênero OU unissex
      - unissex: apenas unissex
    """

    if genero is None:
        cursor.execute(
            """
            SELECT id, nome, apelido, grupo_muscular, descricao, publico_alvo, padrao, series_padrao, repeticoes_padrao
            FROM exercicios
            ORDER BY id;
            """
        )
        rows = cursor.fetchall()
    else:
        genero_norm = genero.lower()
        if genero_norm not in ("masculino", "feminino", "unissex"):
            raise HTTPException(
                status_code=400,
                detail="Gênero inválido. Use 'masculino', 'feminino' ou 'unissex'.",
            )

        if genero_norm == "unissex":
            cursor.execute(
                """
                SELECT id, nome, apelido, grupo_muscular, descricao, publico_alvo, padrao, series_padrao, repeticoes_padrao
                FROM exercicios
                WHERE publico_alvo = 'unissex'
                ORDER BY id;
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, nome, apelido, grupo_muscular, descricao, publico_alvo, padrao, series_padrao, repeticoes_padrao
                FROM exercicios
                WHERE publico_alvo IN (?, 'unissex')
                ORDER BY id;
                """,
                [genero_norm],
            )
        rows = cursor.fetchall()

    return [
        Exercicio(
            id=row[0],
            nome=row[1],
            apelido=row[2],
            grupo_muscular=row[3],
            descricao=row[4],
            publico_alvo=row[5],
            padrao=row[6],
            series_padrao=row[7],
            repeticoes_padrao=row[8],
        )
        for row in rows
    ]


@router.get("/{exercicio_id}", response_model=Exercicio)
def obter_exercicio(exercicio_id: int, cursor=Depends(get_db_cursor)):
    cursor.execute(
        """
        SELECT id, nome, apelido, grupo_muscular, descricao, publico_alvo, padrao, series_padrao, repeticoes_padrao
        FROM exercicios
        WHERE id = ?;
        """,
        [exercicio_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")

    return Exercicio(
            id=row[0],
            nome=row[1],
            apelido=row[2],
            grupo_muscular=row[3],
            descricao=row[4],
            publico_alvo=row[5],
            padrao=row[6],
            series_padrao=row[7],
            repeticoes_padrao=row[8],
        )

@router.put("/{exercicio_id}", response_model=Exercicio)
def atualizar_exercicio(
    exercicio_id: int,
    exercicio: Exercicio,
    cursor=Depends(get_db_cursor),
):
    """
    Atualiza todos os dados de um exercício do catálogo.
    """

    cursor.execute(
        "SELECT id FROM exercicios WHERE id = ?;",
        [exercicio_id],
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")

    cursor.execute(
        """
        UPDATE exercicios
        SET
            nome = ?,
            apelido = ?,
            grupo_muscular = ?,
            descricao = ?,
            series_padrao = ?,
            repeticoes_padrao = ?,
            publico_alvo = ?,
            padrao = ?
        WHERE id = ?;
        """,
        [
            exercicio.nome,
            exercicio.apelido,
            exercicio.grupo_muscular,
            exercicio.descricao,
            exercicio.series_padrao,
            exercicio.repeticoes_padrao,
            exercicio.publico_alvo,
            exercicio.padrao,
            exercicio_id,
        ],
    )

    return Exercicio(
        id=exercicio_id,
        **exercicio.model_dump(exclude={"id"}),
    )

@router.delete("/{exercicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_exercicio(exercicio_id: int, cursor=Depends(get_db_cursor)):
    cursor.execute(
        "DELETE FROM exercicios_do_treino WHERE exercicio_id = ?;",
        [exercicio_id],
    )
    cursor.execute(
        "DELETE FROM exercicios WHERE id = ?;",
        [exercicio_id],
    )
    return
