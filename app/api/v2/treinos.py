from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_cursor
from app.models.treino import Treino, GerarTreinoPorMusculosRequest, TreinoGerado, ReordenarRequest, PerfilType 
from app.models.exercicio_do_treino import ExercicioDoTreino

from app.services.treinos_service import (
    list_treinos,
    get_treino,
    create_treino,
    update_treino,
    delete_treino,
)

from app.services.exercicios_treino_service import (
    create_exercicio_do_treino,
    update_exercicio_do_treino_service,
    list_exercicios_do_treino_service,
    delete_exercicio_do_treino_service,
    reorder_exercicios_do_treino_service,
    adicionar_exercicios_padrao_ao_treino_service,
    gerar_treino_por_musculos_service,
)


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


@router.post("/", response_model=Treino, status_code=status.HTTP_201_CREATED)
def criar_treino(treino: Treino, cursor=Depends(get_db_cursor)):
    return create_treino(cursor, treino)

@router.get("/", response_model=List[Treino])
def listar_treinos_route(cursor=Depends(get_db_cursor)):
    return list_treinos(cursor)

@router.get("/{treino_id}", response_model=Treino)
def obter_treino(treino_id: int, cursor=Depends(get_db_cursor)):
    treino = get_treino(cursor, treino_id)
    if not treino:
        raise HTTPException(status_code=404, detail="Treino não encontrado")
    return treino

@router.put("/{treino_id}", response_model=Treino)
def atualizar_treino_route(
    treino_id: int,
    treino: Treino,
    cursor=Depends(get_db_cursor),
):
    atualizado = update_treino(cursor, treino_id, treino)
    if not atualizado:
        raise HTTPException(status_code=404, detail="Treino não encontrado")
    return atualizado

@router.delete("/{treino_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_treino_route(treino_id: int, cursor=Depends(get_db_cursor)):
    delete_treino(cursor, treino_id)
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

    return create_exercicio_do_treino(cursor, treino_id, exercicio_treino)

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
    """

    atualizado = update_exercicio_do_treino_service(
        cursor, treino_id, exercicio_treino_id, exercicio_treino
    )
    if not atualizado:
        raise HTTPException(
            status_code=404,
            detail="Exercício do treino não encontrado para este treino",
        )

    return atualizado

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
    return list_exercicios_do_treino_service(cursor, treino_id)


@router.post(
    "/{treino_id}/reordenar",
    status_code=status.HTTP_200_OK,
)
def reordenar_exercicios_do_treino(
    treino_id: int,
    payload: ReordenarRequest,
    cursor=Depends(get_db_cursor),
):
    if not payload.ordem:
        raise HTTPException(status_code=400, detail="Lista de ordem vazia.")

    nao_pertencem = reorder_exercicios_do_treino_service(
        cursor, treino_id, payload.ordem
    )

    if nao_pertencem:
        raise HTTPException(
            status_code=400,
            detail=f"IDs não pertencem ao treino: {nao_pertencem}",
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
    perfil: PerfilType = "moderado",
    cursor=Depends(get_db_cursor),
):
    """
    Aplica o padrão de exercícios de um GRUPO MUSCULAR
    a um TREINO já existente, de acordo com o PERFIL.
    """

    resultado = adicionar_exercicios_padrao_ao_treino_service(
        cursor, treino_id, grupo_muscular, perfil
    )

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Treino ou aluno vinculado não encontrado",
        )

    if resultado == []:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Nenhum exercício padrão cadastrado para o grupo "
                f"'{grupo_muscular.lower()}' e perfil/gênero do aluno."
            ),
        )

    return resultado


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

    resultado = gerar_treino_por_musculos_service(
        cursor,
        aluno_id=payload.aluno_id,
        data=payload.data,
        observacoes=payload.observacoes,
        grupos_musculares=payload.grupos_musculares,
        perfil=payload.perfil,
    )

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno não encontrado",
        )

    treino_model, exercicios_criados = resultado

    return TreinoGerado(
        treino=treino_model,
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
    removido = delete_exercicio_do_treino_service(
        cursor, treino_id, exercicio_treino_id
    )
    if not removido:
        raise HTTPException(
            status_code=404,
            detail="Exercício do treino não encontrado para este treino",
        )
    return
