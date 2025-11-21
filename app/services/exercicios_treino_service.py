# app/services/exercicios_treino_service.py

from typing import List, Optional, Tuple
from datetime import date

from app.models.exercicio_do_treino import ExercicioDoTreino
from app.models.treino import Treino


# ---------- UTIL ----------


def ajustar_series_repeticoes(
    series_padrao: int, repeticoes_padrao: int, perfil: str
) -> Tuple[int, int]:
    """
    Ajusta séries e repetições de acordo com o perfil:

    - leve: 1 série a menos (>=1) e 80% das repetições (>=1)
    - moderado: igual ao padrão
    - intenso: 1 série a mais e 120% das repetições (arredondado, >=1)
    """
    perfil = perfil.lower()
    if perfil == "leve":
        series = max(1, series_padrao - 1)
        reps = max(1, int(repeticoes_padrao * 0.8))
    elif perfil == "intenso":
        series = series_padrao + 1
        reps = max(1, int(repeticoes_padrao * 1.2))
    else:  # moderado ou qualquer outro valor
        series = series_padrao
        reps = repeticoes_padrao

    return series, reps


# ---------- CRUD EXERCÍCIOS DO TREINO ----------


def create_exercicio_do_treino(
    cursor, treino_id: int, exercicio_treino: ExercicioDoTreino
) -> ExercicioDoTreino:
    """
    Cria um registro em exercicios_do_treino para um treino.
    Não valida se treino/exercicio existem (a rota faz isso).
    Também define a próxima 'ordem' disponível.
    """

    cursor.execute(
        "SELECT COALESCE(MAX(ordem), 0) FROM exercicios_do_treino WHERE treino_id = ?;",
        [treino_id],
    )
    max_ordem = cursor.fetchone()[0]
    nova_ordem = max_ordem + 1

    cursor.execute(
        """
        INSERT INTO exercicios_do_treino (
            id, treino_id, exercicio_id, series, repeticoes, carga, observacoes, ordem
        )
        VALUES (nextval('exercicios_do_treino_seq'), ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        [
            treino_id,
            exercicio_treino.exercicio_id,
            exercicio_treino.series,
            exercicio_treino.repeticoes,
            exercicio_treino.carga,
            exercicio_treino.observacoes,
            nova_ordem,
        ],
    )
    new_id = cursor.fetchone()[0]

    return ExercicioDoTreino(
        id=new_id,
        treino_id=treino_id,
        exercicio_id=exercicio_treino.exercicio_id,
        series=exercicio_treino.series,
        repeticoes=exercicio_treino.repeticoes,
        carga=exercicio_treino.carga,
        observacoes=exercicio_treino.observacoes,
    )


def update_exercicio_do_treino_service(
    cursor,
    treino_id: int,
    exercicio_treino_id: int,
    exercicio_treino: ExercicioDoTreino,
) -> Optional[ExercicioDoTreino]:
    """
    Atualiza um registro existente em exercicios_do_treino.
    Retorna None se não existir ou não pertencer ao treino.
    """

    cursor.execute(
        """
        SELECT exercicio_id
        FROM exercicios_do_treino
        WHERE id = ? AND treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    exercicio_id_existente = row[0]

    cursor.execute(
        """
        UPDATE exercicios_do_treino
        SET
            series = ?,
            repeticoes = ?,
            carga = ?,
            observacoes = ?
        WHERE id = ? AND treino_id = ?;
        """,
        [
            exercicio_treino.series,
            exercicio_treino.repeticoes,
            exercicio_treino.carga,
            exercicio_treino.observacoes,
            exercicio_treino_id,
            treino_id,
        ],
    )

    return ExercicioDoTreino(
        id=exercicio_treino_id,
        treino_id=treino_id,
        exercicio_id=exercicio_id_existente,
        series=exercicio_treino.series,
        repeticoes=exercicio_treino.repeticoes,
        carga=exercicio_treino.carga,
        observacoes=exercicio_treino.observacoes,
    )


def list_exercicios_do_treino_service(
    cursor,
    treino_id: int,
) -> List[ExercicioDoTreino]:
    """
    Lista exercícios de um treino, ordenados por 'ordem' e id.
    """
    cursor.execute(
        """
        SELECT
            id,
            treino_id,
            exercicio_id,
            series,
            repeticoes,
            carga,
            observacoes,
            ordem
        FROM exercicios_do_treino
        WHERE treino_id = ?
        ORDER BY ordem, id;
        """,
        [treino_id],
    )
    rows = cursor.fetchall()
    return [
        ExercicioDoTreino(
            id=row[0],
            treino_id=row[1],
            exercicio_id=row[2],
            series=row[3],
            repeticoes=row[4],
            carga=row[5],
            observacoes=row[6],
        )
        for row in rows
    ]


def delete_exercicio_do_treino_service(
    cursor,
    treino_id: int,
    exercicio_treino_id: int,
) -> bool:
    """
    Remove um exercício do treino.
    Retorna False se não existir para este treino.
    """
    cursor.execute(
        """
        SELECT id
        FROM exercicios_do_treino
        WHERE id = ? AND treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return False

    cursor.execute(
        """
        DELETE FROM exercicios_do_treino
        WHERE id = ? AND treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    return True


def reorder_exercicios_do_treino_service(
    cursor,
    treino_id: int,
    ordem_ids: List[int],
) -> List[int]:
    """
    Reordena os exercícios de um treino.
    Retorna a lista de IDs que NÃO pertencem ao treino, se houver.
    """

    cursor.execute(
        """
        SELECT id
        FROM exercicios_do_treino
        WHERE treino_id = ?;
        """,
        [treino_id],
    )
    existentes = {row[0] for row in cursor.fetchall()}

    nao_pertencem = [x for x in ordem_ids if x not in existentes]
    if nao_pertencem:
        return nao_pertencem

    for posicao, exercicio_treino_id in enumerate(ordem_ids, start=1):
        cursor.execute(
            """
            UPDATE exercicios_do_treino
            SET ordem = ?
            WHERE id = ? AND treino_id = ?;
            """,
            [posicao, exercicio_treino_id, treino_id],
        )

    return []


# ---------- PADRÃO E GERAÇÃO DE TREINO ----------


def adicionar_exercicios_padrao_ao_treino_service(
    cursor,
    treino_id: int,
    grupo_muscular: str,
    perfil: str,
) -> Optional[List[ExercicioDoTreino]]:
    """
    Adiciona exercícios padrão de um grupo muscular a um treino existente,
    respeitando o gênero do aluno e o perfil.

    Retorno:
        - None -> treino/aluno não encontrado
        - [] -> nenhum exercício padrão encontrado para esse grupo/gênero
        - [ExercicioDoTreino, ...] -> lista criada
    """

    grupo_norm = grupo_muscular.lower()

    # Buscar aluno_id a partir do treino
    cursor.execute(
        "SELECT aluno_id FROM treinos WHERE id = ?;",
        [treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    aluno_id = row[0]

    # Buscar gênero do aluno
    cursor.execute(
        "SELECT genero FROM alunos WHERE id = ?;",
        [aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    genero_aluno = row[0]  # masculino / feminino / unissex

    # Buscar exercícios padrão naquele grupo e gênero
    if genero_aluno == "unissex":
        cursor.execute(
            """
            SELECT id, series_padrao, repeticoes_padrao
            FROM exercicios
            WHERE padrao = TRUE
              AND lower(grupo_muscular) = ?
              AND publico_alvo = 'unissex'
            ORDER BY id;
            """,
            [grupo_norm],
        )
    else:
        cursor.execute(
            """
            SELECT id, series_padrao, repeticoes_padrao
            FROM exercicios
            WHERE padrao = TRUE
              AND lower(grupo_muscular) = ?
              AND publico_alvo IN (?, 'unissex')
            ORDER BY id;
            """,
            [grupo_norm, genero_aluno],
        )

    rows = cursor.fetchall()
    if not rows:
        return []

    # Descobrir ordem inicial
    cursor.execute(
        "SELECT COALESCE(MAX(ordem), 0) FROM exercicios_do_treino WHERE treino_id = ?;",
        [treino_id],
    )
    max_ordem = cursor.fetchone()[0]
    ordem_atual = max_ordem

    obs_exercicio = f"séries/repetições conforme padrão ({perfil})"

    criados: List[ExercicioDoTreino] = []

    for row in rows:
        exercicio_id = row[0]
        series_padrao = row[1]
        repeticoes_padrao = row[2]

        series, repeticoes = ajustar_series_repeticoes(
            series_padrao, repeticoes_padrao, perfil
        )

        ordem_atual += 1

        cursor.execute(
            """
            INSERT INTO exercicios_do_treino (
                id, treino_id, exercicio_id, series, repeticoes, carga, observacoes, ordem
            )
            VALUES (nextval('exercicios_do_treino_seq'), ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            [
                treino_id,
                exercicio_id,
                series,
                repeticoes,
                None,
                obs_exercicio,
                ordem_atual,
            ],
        )
        new_id = cursor.fetchone()[0]

        criados.append(
            ExercicioDoTreino(
                id=new_id,
                treino_id=treino_id,
                exercicio_id=exercicio_id,
                series=series,
                repeticoes=repeticoes,
                carga=None,
                observacoes=obs_exercicio,
            )
        )

    return criados


def gerar_treino_por_musculos_service(
    cursor,
    aluno_id: int,
    data: date,
    observacoes: Optional[str],
    grupos_musculares: List[str],
    perfil: str,
) -> Optional[tuple[Treino, List[ExercicioDoTreino]]]:
    """
    Gera um treino completo para um aluno:

    - Cria 1 registro em treinos
    - Cria N registros em exercicios_do_treino a partir dos grupos musculares
    - Aplica filtros de gênero e padrão
    - Ajusta séries/reps conforme perfil

    Retorno:
        - None -> aluno não encontrado
        - (Treino, [ExercicioDoTreino...]) -> treino gerado (lista pode ser vazia)
    """

    if not grupos_musculares:
        return None

    # Verificar aluno e obter gênero
    cursor.execute(
        "SELECT genero FROM alunos WHERE id = ?;",
        [aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        return None

    genero_aluno = row[0]

    obs_treino = observacoes or (
        f"Treino gerado por músculos ({', '.join(grupos_musculares)}) "
        f"perfil={perfil}"
    )

    # Criar treino
    cursor.execute(
        """
        INSERT INTO treinos (id, aluno_id, data, observacoes)
        VALUES (nextval('treinos_seq'), ?, ?, ?)
        RETURNING id;
        """,
        [aluno_id, data, obs_treino],
    )
    treino_id = cursor.fetchone()[0]

    treino_model = Treino(
        id=treino_id,
        aluno_id=aluno_id,
        data=data,
        observacoes=obs_treino,
    )

    exercicios_criados: List[ExercicioDoTreino] = []

    # Descobrir ordem inicial
    cursor.execute(
        "SELECT COALESCE(MAX(ordem), 0) FROM exercicios_do_treino WHERE treino_id = ?;",
        [treino_id],
    )
    max_ordem = cursor.fetchone()[0]
    ordem_atual = max_ordem

    for grupo in grupos_musculares:
        grupo_norm = grupo.lower()

        # Buscar exercícios padrão para o grupo e gênero
        if genero_aluno == "unissex":
            cursor.execute(
                """
                SELECT id, series_padrao, repeticoes_padrao
                FROM exercicios
                WHERE padrao = TRUE
                  AND lower(grupo_muscular) = ?
                  AND publico_alvo = 'unissex'
                ORDER BY id;
                """,
                [grupo_norm],
            )
        else:
            cursor.execute(
                """
                SELECT id, series_padrao, repeticoes_padrao
                FROM exercicios
                WHERE padrao = TRUE
                  AND lower(grupo_muscular) = ?
                  AND publico_alvo IN (?, 'unissex')
                ORDER BY id;
                """,
                [grupo_norm, genero_aluno],
            )

        rows = cursor.fetchall()
        if not rows:
            continue

        obs_exercicio = f"séries/repetições conforme padrão ({perfil})"

        for row in rows:
            exercicio_id = row[0]
            series_padrao = row[1]
            repeticoes_padrao = row[2]

            series, repeticoes = ajustar_series_repeticoes(
                series_padrao, repeticoes_padrao, perfil
            )

            ordem_atual += 1

            cursor.execute(
                """
                INSERT INTO exercicios_do_treino (
                    id, treino_id, exercicio_id, series, repeticoes, carga, observacoes, ordem
                )
                VALUES (nextval('exercicios_do_treino_seq'), ?, ?, ?, ?, ?, ?, ?)
                RETURNING id;
                """,
                [
                    treino_id,
                    exercicio_id,
                    series,
                    repeticoes,
                    None,
                    obs_exercicio,
                    ordem_atual,
                ],
            )
            new_id = cursor.fetchone()[0]

            exercicios_criados.append(
                ExercicioDoTreino(
                    id=new_id,
                    treino_id=treino_id,
                    exercicio_id=exercicio_id,
                    series=series,
                    repeticoes=repeticoes,
                    carga=None,
                    observacoes=obs_exercicio,
                )
            )

    return treino_model, exercicios_criados
