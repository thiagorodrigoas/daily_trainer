# app/services/treinos_service.py

from typing import List, Optional, Dict, Any
from datetime import date

from app.models.treino import Treino
from app.models.exercicio_do_treino import ExercicioDoTreino


# ---------- TREINOS (sessão do dia) ----------


def list_treinos(cursor) -> List[Treino]:
    cursor.execute(
        """
        SELECT id, aluno_id, data, observacoes
        FROM treinos
        ORDER BY data DESC, id DESC;
        """
    )
    rows = cursor.fetchall()
    return [
        Treino(
            id=row[0],
            aluno_id=row[1],
            data=row[2],
            observacoes=row[3],
        )
        for row in rows
    ]


def get_treino(cursor, treino_id: int) -> Optional[Treino]:
    cursor.execute(
        """
        SELECT id, aluno_id, data, observacoes
        FROM treinos
        WHERE id = ?;
        """,
        [treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    return Treino(
        id=row[0],
        aluno_id=row[1],
        data=row[2],
        observacoes=row[3],
    )


def create_treino(cursor, treino: Treino) -> Treino:
    cursor.execute(
        """
        INSERT INTO treinos (id, aluno_id, data, observacoes)
        VALUES (nextval('treinos_seq'), ?, ?, ?)
        RETURNING id;
        """,
        [treino.aluno_id, treino.data, treino.observacoes],
    )
    new_id = cursor.fetchone()[0]
    return Treino(
        id=new_id,
        **treino.model_dump(exclude={"id"}),
    )


def update_treino(cursor, treino_id: int, treino: Treino) -> Optional[Treino]:
    # Confirma que o treino existe
    cursor.execute(
        "SELECT id FROM treinos WHERE id = ?;",
        [treino_id],
    )
    if cursor.fetchone() is None:
        return None

    # Valida FK do aluno para evitar erro de constraint
    cursor.execute(
        "SELECT id FROM alunos WHERE id = ?;",
        [treino.aluno_id],
    )
    if cursor.fetchone() is None:
        return None

    cursor.execute(
        """
        UPDATE treinos
        SET data = ?, observacoes = ?
        WHERE id = ?;
        """,
        [
            # treino.aluno_id,
            treino.data,
            treino.observacoes,
            treino_id,
        ],
    )

    return Treino(
        id=treino_id,
        **treino.model_dump(exclude={"id"}),
    )


def delete_treino(cursor, treino_id: int) -> bool:
    # Primeiro apagamos exercícios vinculados (pra evitar erro de FK)
    cursor.execute(
        "DELETE FROM exercicios_do_treino WHERE treino_id = ?;",
        [treino_id],
    )
    cursor.execute(
        "DELETE FROM treinos WHERE id = ?;",
        [treino_id],
    )
    return True


# ---------- TREINOS PARA WEB (com nome do aluno) ----------


def list_treinos_with_aluno(cursor) -> List[Dict[str, Any]]:
    """
    Versão para frontend web: inclui nome do aluno junto com o treino.
    """
    cursor.execute(
        """
        SELECT t.id, t.aluno_id, t.data, t.observacoes, a.nome
        FROM treinos t
        JOIN alunos a ON a.id = t.aluno_id
        ORDER BY t.data DESC, t.id DESC;
        """
    )
    rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "aluno_id": row[1],
            "data": row[2],
            "observacoes": row[3],
            "aluno_nome": row[4],
        }
        for row in rows
    ]
