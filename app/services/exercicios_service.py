# app/services/exercicios_service.py

from typing import List, Optional

from app.models.exercicio import Exercicio


def list_exercicios(
    cursor,
    genero: Optional[str] = None,
) -> List[Exercicio]:
    """
    Lista exercícios do catálogo.
    Se 'genero' for informado (masculino/feminino/unissex), aplica filtro:
      - masculino/feminino: exercícios daquele gênero OU unissex
      - unissex: apenas unissex

    Levanta ValueError se o gênero for inválido.
    """

    if genero is None:
        cursor.execute(
            """
            SELECT
                id,
                nome,
                apelido,
                grupo_muscular,
                descricao,
                series_padrao,
                repeticoes_padrao,
                publico_alvo,
                padrao
            FROM exercicios
            ORDER BY grupo_muscular, nome;
            """
        )
        rows = cursor.fetchall()
    else:
        genero_norm = genero.lower()
        if genero_norm not in ("masculino", "feminino", "unissex"):
            raise ValueError("genero_invalido")

        if genero_norm == "unissex":
            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    apelido,
                    grupo_muscular,
                    descricao,
                    series_padrao,
                    repeticoes_padrao,
                    publico_alvo,
                    padrao
                FROM exercicios
                WHERE publico_alvo = 'unissex'
                ORDER BY grupo_muscular, nome;
                """
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    apelido,
                    grupo_muscular,
                    descricao,
                    series_padrao,
                    repeticoes_padrao,
                    publico_alvo,
                    padrao
                FROM exercicios
                WHERE publico_alvo IN (?, 'unissex')
                ORDER BY grupo_muscular, nome;
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
            series_padrao=row[5],
            repeticoes_padrao=row[6],
            publico_alvo=row[7],
            padrao=row[8],
        )
        for row in rows
    ]


def get_exercicio(cursor, exercicio_id: int) -> Optional[Exercicio]:
    cursor.execute(
        """
        SELECT
            id,
            nome,
            apelido,
            grupo_muscular,
            descricao,
            series_padrao,
            repeticoes_padrao,
            publico_alvo,
            padrao
        FROM exercicios
        WHERE id = ?;
        """,
        [exercicio_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    return Exercicio(
        id=row[0],
        nome=row[1],
        apelido=row[2],
        grupo_muscular=row[3],
        descricao=row[4],
        series_padrao=row[5],
        repeticoes_padrao=row[6],
        publico_alvo=row[7],
        padrao=row[8],
    )


def create_exercicio(cursor, exercicio: Exercicio) -> Exercicio:
    cursor.execute(
        """
        INSERT INTO exercicios (
            id,
            nome,
            apelido,
            grupo_muscular,
            descricao,
            series_padrao,
            repeticoes_padrao,
            publico_alvo,
            padrao
        )
        VALUES (nextval('exercicios_seq'), ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
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
        ],
    )
    new_id = cursor.fetchone()[0]
    return Exercicio(
        id=new_id,
        **exercicio.model_dump(exclude={"id"}),
    )


def update_exercicio(
    cursor,
    exercicio_id: int,
    exercicio: Exercicio,
) -> Optional[Exercicio]:
    cursor.execute(
        "SELECT id FROM exercicios WHERE id = ?;",
        [exercicio_id],
    )
    if cursor.fetchone() is None:
        return None

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


def delete_exercicio(cursor, exercicio_id: int) -> bool:
    """
    Remove um exercício do catálogo.
    Também remove referências em exercicios_do_treino.
    Retorna False se o exercício não existir.
    """

    cursor.execute(
        "SELECT id FROM exercicios WHERE id = ?;",
        [exercicio_id],
    )
    if cursor.fetchone() is None:
        return False

    # Remove vinculações em treinos (opcional, mas ajuda a evitar lixo)
    cursor.execute(
        "DELETE FROM exercicios_do_treino WHERE exercicio_id = ?;",
        [exercicio_id],
    )

    cursor.execute(
        "DELETE FROM exercicios WHERE id = ?;",
        [exercicio_id],
    )
    return True
