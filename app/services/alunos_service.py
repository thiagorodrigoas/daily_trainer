# app/services/alunos_service.py

from typing import List, Optional

from app.models.aluno import Aluno


def list_alunos(cursor) -> List[Aluno]:
    cursor.execute(
        """
        SELECT id, nome, genero, telefone, turma, observacoes
        FROM alunos
        ORDER BY nome;
        """
    )
    rows = cursor.fetchall()
    return [
        Aluno(
            id=row[0],
            nome=row[1],
            genero=row[2],
            telefone=row[3],
            turma=row[4],
            observacoes=row[5],
        )
        for row in rows
    ]


def get_aluno(cursor, aluno_id: int) -> Optional[Aluno]:
    cursor.execute(
        """
        SELECT id, nome, genero, telefone, turma, observacoes
        FROM alunos
        WHERE id = ?;
        """,
        [aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    return Aluno(
        id=row[0],
        nome=row[1],
        genero=row[2],
        telefone=row[3],
        turma=row[4],
        observacoes=row[5],
    )


def create_aluno(cursor, aluno: Aluno) -> Aluno:
    cursor.execute(
        """
        INSERT INTO alunos (id, nome, genero, telefone, turma, observacoes)
        VALUES (nextval('alunos_seq'), ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        [aluno.nome, aluno.genero, aluno.telefone, aluno.turma, aluno.observacoes],
    )
    new_id = cursor.fetchone()[0]
    return Aluno(
        id=new_id,
        **aluno.model_dump(exclude={"id"}),
    )


def update_aluno(cursor, aluno_id: int, aluno: Aluno) -> Optional[Aluno]:
    # verifica se existe
    cursor.execute(
        "SELECT id FROM alunos WHERE id = ?;",
        [aluno_id],
    )
    if cursor.fetchone() is None:
        return None

    cursor.execute(
        """
        UPDATE alunos
        SET nome = ?, genero = ?, telefone = ?, turma = ?, observacoes = ?
        WHERE id = ?;
        """,
        [
            aluno.nome,
            aluno.genero,
            aluno.telefone,
            aluno.turma,
            aluno.observacoes,
            aluno_id,
        ],
    )

    return Aluno(
        id=aluno_id,
        **aluno.model_dump(exclude={"id"}),
    )


def delete_aluno(cursor, aluno_id: int) -> bool:
    # Remove exercícios dos treinos do aluno
    cursor.execute(
        """
        DELETE FROM exercicios_do_treino
        WHERE treino_id IN (SELECT id FROM treinos WHERE aluno_id = ?);
        """,
        [aluno_id],
    )
    # Remove treinos do aluno
    cursor.execute("DELETE FROM treinos WHERE aluno_id = ?;", [aluno_id])

    # Remove o aluno
    cursor.execute("DELETE FROM alunos WHERE id = ?;", [aluno_id])

    # Opcionalmente poderíamos checar rowcount, mas DuckDB não expõe fácil
    return True
