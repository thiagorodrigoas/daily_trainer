from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.treino import Treino, GerarTreinoPorMusculosRequest, TreinoGerado, ReordenarRequest, PerfilType 
from app.models.exercicio_do_treino import ExercicioDoTreino

router = APIRouter(prefix="/treinos", tags=["treinos"])


def get_db_cursor():
    with get_cursor() as cursor:
        yield cursor

def ajustar_series_repeticoes(
    series_padrao: int, repeticoes_padrao: int, perfil: PerfilType
) -> Tuple[int, int]:
    """
    Ajusta séries e repetições de acordo com o perfil:

    - leve: 1 série a menos (>=1) e 80% das repetições (>=1)
    - moderado: igual ao padrão
    - intenso: 1 série a mais e 120% das repetições (arredondado, >=1)
    """
    if perfil == "leve":
        series = max(1, series_padrao - 1)
        reps = max(1, int(repeticoes_padrao * 0.8))
    elif perfil == "intenso":
        series = series_padrao + 1
        reps = max(1, int(repeticoes_padrao * 1.2))
    else:  # moderado
        series = series_padrao
        reps = repeticoes_padrao

    return series, reps

def get_or_create_exercicio(
    cursor,
    nome: str,
    apelido: str | None = None,
    grupo_muscular: str | None = None,
    publico_alvo: str = "unissex",
) -> int:
    """
    Retorna o ID do exercício com o nome e publico_alvo informados.
    Se não existir, cria no catálogo de exercicios.
    """
    cursor.execute(
        "SELECT id FROM exercicios WHERE nome = ? AND publico_alvo = ?;",
        [nome, publico_alvo],
    )
    row = cursor.fetchone()
    if row:
        return row[0]


    apelido_final = apelido or nome
    
    cursor.execute(
        """
        INSERT INTO exercicios (id, nome, apelido, grupo_muscular, descricao, publico_alvo)
        VALUES (nextval('exercicios_seq'), ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        [nome, apelido_final, grupo_muscular, None, publico_alvo],
    )
    return cursor.fetchone()[0]


# ---------- LISTAR PADRÃO (SEM GRAVAR) ---------- #


@router.get("/padroes/{grupo_muscular}")
@router.get("/padroes/{grupo_muscular}")
def listar_exercicios_padrao(
    grupo_muscular: str,
    genero: str,
    cursor=Depends(get_db_cursor),
):
    """
    Retorna a LISTA PADRÃO de exercícios para um grupo muscular e gênero,
    SEM gravar nada no banco.

    - genero: 'masculino', 'feminino' ou 'unissex'
    - Exercícios retornados:
        - padrao = TRUE
        - grupo_muscular (case-insensitive)
        - específicos do gênero OU 'unissex'
        - séries/repetições vindas de series_padrao/repeticoes_padrao
    """
    grupo_norm = grupo_muscular.lower()
    genero_norm = genero.lower()

    if genero_norm not in ("masculino", "feminino", "unissex"):
        raise HTTPException(
            status_code=400,
            detail="Gênero inválido. Use 'masculino', 'feminino' ou 'unissex'.",
        )

    if genero_norm == "unissex":
        cursor.execute(
            """
            SELECT
                nome,
                apelido,
                grupo_muscular,
                series_padrao,
                repeticoes_padrao,
                publico_alvo
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
            SELECT
                nome,
                apelido,
                grupo_muscular,
                series_padrao,
                repeticoes_padrao,
                publico_alvo
            FROM exercicios
            WHERE padrao = TRUE
              AND lower(grupo_muscular) = ?
              AND publico_alvo IN (?, 'unissex')
            ORDER BY id;
            """,
            [grupo_norm, genero_norm],
        )

    rows = cursor.fetchall()
    obs_exercicio = "séries/repetições padrão do exercício"

    resultado = []
    for row in rows:
        resultado.append(
            {
                "nome": row[0],
                "apelido": row[1],
                "grupo_muscular": row[2],
                "series": row[3],
                "repeticoes": row[4],
                "publico_alvo": row[5],
                "observacoes": obs_exercicio,
            }
        )

    return resultado



# ---------- TREINOS (sessão do dia) ---------- #


@router.post(
    "/", response_model=Treino, status_code=status.HTTP_201_CREATED
)
def criar_treino(treino: Treino, cursor=Depends(get_db_cursor)):
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


@router.get("/", response_model=List[Treino])
def listar_treinos(cursor=Depends(get_db_cursor)):
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


@router.get("/{treino_id}", response_model=Treino)
def obter_treino(treino_id: int, cursor=Depends(get_db_cursor)):
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
        raise HTTPException(status_code=404, detail="Treino não encontrado")

    return Treino(
        id=row[0],
        aluno_id=row[1],
        data=row[2],
        observacoes=row[3],
    )

@router.put("/{treino_id}", response_model=Treino)
def atualizar_treino(
    treino_id: int,
    treino: Treino,
    cursor=Depends(get_db_cursor),
):
    """
    Atualiza os dados básicos de um treino (sessão do dia).
    """

    cursor.execute(
        "SELECT id FROM treinos WHERE id = ?;",
        [treino_id],
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Treino não encontrado")

    cursor.execute(
        """
        UPDATE treinos
        SET aluno_id = ?, data = ?, observacoes = ?
        WHERE id = ?;
        """,
        [
            treino.aluno_id,
            treino.data,
            treino.observacoes,
            treino_id,
        ],
    )

    return Treino(
        id=treino_id,
        **treino.model_dump(exclude={"id"}),
    )

@router.delete("/{treino_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_treino(treino_id: int, cursor=Depends(get_db_cursor)):
    # Primeiro apagamos exercícios vinculados (pra evitar erro de FK)
    cursor.execute(
        "DELETE FROM exercicios_do_treino WHERE treino_id = ?;",
        [treino_id],
    )
    cursor.execute(
        "DELETE FROM treinos WHERE id = ?;",
        [treino_id],
    )
    return


# ---------- EXERCÍCIOS DO TREINO (CRUD SIMPLES) ---------- #


@router.post(
    "/{treino_id}/exercicios",
    response_model=ExercicioDoTreino,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_exercicio_ao_treino(
    treino_id: int,
    exercicio_treino: ExercicioDoTreino,
    cursor=Depends(get_db_cursor),
):
    """
    Adiciona um exercício a um treino específico.
    O treino_id da URL sobrescreve o treino_id do body, se vier.
    """

    # verificar se treino existe
    cursor.execute("SELECT id FROM treinos WHERE id = ?;", [treino_id])
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Treino não encontrado")

    # verificar se exercício existe
    cursor.execute(
        "SELECT id FROM exercicios WHERE id = ?;",
        [exercicio_treino.exercicio_id],
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    
    # Descobre a maior ordem atual
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
            nova_ordem
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

@router.put(
    "/{treino_id}/exercicios/{exercicio_treino_id}",
    response_model=ExercicioDoTreino,
)
def atualizar_exercicio_do_treino(
    treino_id: int,
    exercicio_treino_id: int,
    exercicio_treino: ExercicioDoTreino,
    cursor=Depends(get_db_cursor),
):
    """
    Atualiza um exercício específico dentro de um treino.
    Pode ajustar séries, repetições, carga e observações.
    """

    # Verifica se registro existe e pertence ao treino
    cursor.execute(
        """
        SELECT id, exercicio_id
        FROM exercicios_do_treino
        WHERE id = ? AND treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Exercício do treino não encontrado para este treino",
        )

    # Se quiser permitir trocar o exercicio_id, também pode usar exercicio_treino.exercicio_id aqui
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
        exercicio_id=exercicio_treino.exercicio_id,
        series=exercicio_treino.series,
        repeticoes=exercicio_treino.repeticoes,
        carga=exercicio_treino.carga,
        observacoes=exercicio_treino.observacoes,
    )

@router.get(
    "/{treino_id}/exercicios",
    response_model=List[ExercicioDoTreino],
)
def listar_exercicios_do_treino(
    treino_id: int,
    cursor=Depends(get_db_cursor),
):
    cursor.execute(
        """
        SELECT
            id,
            treino_id,
            exercicio_id,
            series,
            repeticoes,
            carga,
            observacoes
        FROM exercicios_do_treino
        WHERE treino_id = ?
        ORDER BY id;
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


@router.post(
    "/{treino_id}/reordenar",
    status_code=status.HTTP_200_OK,
)
def reordenar_exercicios_do_treino(
    treino_id: int,
    payload: ReordenarRequest,
    cursor=Depends(get_db_cursor),
):
    """
    Reordena os exercícios de um treino.
    Recebe uma lista de IDs (exercicios_do_treino) na ordem desejada.

    Exemplo:
    {
        "ordem": [15, 12, 10, 8]
    }
    """

    if not payload.ordem:
        raise HTTPException(status_code=400, detail="Lista de ordem vazia.")

    # Verificar se todos pertencem ao treino
    cursor.execute(
        """
        SELECT id
        FROM exercicios_do_treino
        WHERE treino_id = ?;
        """,
        [treino_id],
    )
    existentes = {row[0] for row in cursor.fetchall()}

    nao_pertencem = [x for x in payload.ordem if x not in existentes]
    if nao_pertencem:
        raise HTTPException(
            status_code=400,
            detail=f"IDs não pertencem ao treino: {nao_pertencem}",
        )

    # Atualizar ordem um por um
    for posicao, exercicio_treino_id in enumerate(payload.ordem, start=1):
        cursor.execute(
            """
            UPDATE exercicios_do_treino
            SET ordem = ?
            WHERE id = ? AND treino_id = ?;
            """,
            [posicao, exercicio_treino_id, treino_id],
        )

    return {"status": "ok", "mensagem": "Ordem atualizada com sucesso"}


# ---------- APLICAR PADRÃO A UM TREINO EXISTENTE ---------- #


@router.post(
    "/{treino_id}/padrao/{grupo_muscular}",
    response_model=List[ExercicioDoTreino],
    status_code=status.HTTP_201_CREATED,
)
def adicionar_exercicios_padrao_ao_treino(
    treino_id: int,
    grupo_muscular: str,
    cursor=Depends(get_db_cursor),
):
    """
    Aplica o padrão de exercícios de um GRUPO MUSCULAR
    a um TREINO já existente.

    - Busca o gênero do aluno a partir do treino
    - Filtra exercícios padrão:
        - específicos do gênero
        - ou 'unissex'
    - Cria os registros em exercicios_do_treino
    - Retorna a lista criada
    """

    grupo_key = grupo_muscular.lower()

    cursor.execute("""SELECT distinct lower(grupo_muscular) AS grupo_muscular FROM exercicios; """)
    grupos_musculares = cursor.fetchall()

    if grupo_key not in grupos_musculares:
        raise HTTPException(
            status_code=400,
            detail=f"Grupo muscular '{grupo_muscular}' não possui treino padrão configurado.",
        )

    # Buscar aluno_id a partir do treino
    cursor.execute(
        "SELECT aluno_id FROM treinos WHERE id = ?;",
        [treino_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Treino não encontrado")

    aluno_id = row[0]

    # Buscar gênero do aluno
    cursor.execute(
        "SELECT genero FROM alunos WHERE id = ?;",
        [aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aluno não encontrado vinculado ao treino")

    genero_aluno = row[0]  # masculino / feminino / unissex

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
            [grupo_key],
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
            [grupo_key, genero_aluno],
        )

    rows = cursor.fetchall()

    if not rows:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Nenhum exercício padrão disponível para o grupo '{grupo_key}' "
                f"e gênero '{genero_aluno}'."
            ),
        )


    obs_exercicio = "séries/repetições conforme padrão do exercício"

    criados: List[ExercicioDoTreino] = []


    for row in rows:
        exercicio_id = row[0]
        series = row[1]
        repeticoes = row[2]

        cursor.execute(
            """
            INSERT INTO exercicios_do_treino (
                id, treino_id, exercicio_id, series, repeticoes, carga, observacoes
            )
            VALUES (nextval('exercicios_do_treino_seq'), ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            [
                treino_id,
                exercicio_id,
                series,
                repeticoes,
                None,
                obs_exercicio,
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



@router.post(
    "/gerar_por_musculos",
    response_model=TreinoGerado,
    status_code=status.HTTP_201_CREATED,
)
def gerar_treino_por_musculos(
    payload: GerarTreinoPorMusculosRequest,
    cursor=Depends(get_db_cursor),
):
    """
    Gera um TREINO COMPLETO, criando:

    - 1 registro em 'treinos' para o aluno informado
    - vários registros em 'exercicios_do_treino' com base em:
        - lista de grupos musculares
        - gênero do aluno
        - exercícios marcados como padrao=TRUE
        - séries/reps ajustadas pelo 'perfil'
    """

    if not payload.grupos_musculares:
        raise HTTPException(
            status_code=400,
            detail="É necessário informar ao menos um grupo_muscular.",
        )

    # Verificar se aluno existe e obter gênero
    cursor.execute(
        "SELECT genero FROM alunos WHERE id = ?;",
        [payload.aluno_id],
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    genero_aluno = row[0]

    # Criar treino
    obs_treino = payload.observacoes or (
        f"Treino gerado por músculos ({', '.join(payload.grupos_musculares)}) "
        f"perfil={payload.perfil}"
    )

    cursor.execute(
        """
        INSERT INTO treinos (id, aluno_id, data, observacoes)
        VALUES (nextval('treinos_seq'), ?, ?, ?)
        RETURNING id;
        """,
        [payload.aluno_id, payload.data, obs_treino],
    )
    treino_id = cursor.fetchone()[0]

    exercicios_criados: List[ExercicioDoTreino] = []

    # Para cada grupo muscular, aplicar padrão ao treino recém-criado
    for grupo in payload.grupos_musculares:
        grupo_norm = grupo.lower()

        # Buscar exercícios padrão naquele grupo/gênero
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
            # Apenas pula esse grupo, mas poderia dar erro se você preferir
            continue

        obs_exercicio = (
            f"séries/repetições conforme padrão ({payload.perfil})"
        )

        for row in rows:
            exercicio_id = row[0]
            series_padrao = row[1]
            repeticoes_padrao = row[2]

            series, repeticoes = ajustar_series_repeticoes(
                series_padrao, repeticoes_padrao, payload.perfil
            )

            cursor.execute(
                """
                INSERT INTO exercicios_do_treino (
                    id, treino_id, exercicio_id, series, repeticoes, carga, observacoes
                )
                VALUES (nextval('exercicios_do_treino_seq'), ?, ?, ?, ?, ?, ?)
                RETURNING id;
                """,
                [
                    treino_id,
                    exercicio_id,
                    series,
                    repeticoes,
                    None,
                    obs_exercicio,
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

    treino_resp = Treino(
        id=treino_id,
        aluno_id=payload.aluno_id,
        data=payload.data,
        observacoes=obs_treino,
    )

    return TreinoGerado(
        treino=treino_resp,
        exercicios=exercicios_criados,
    )


@router.delete(
    "/{treino_id}/exercicios/{exercicio_treino_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remover_exercicio_do_treino(
    treino_id: int,
    exercicio_treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Remove um exercício específico de um treino.
    """

    # Verifica se o registro pertence ao treino informado
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
        raise HTTPException(
            status_code=404,
            detail="Exercício do treino não encontrado para este treino",
        )

    cursor.execute(
        """
        DELETE FROM exercicios_do_treino
        WHERE id = ? AND treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    return
