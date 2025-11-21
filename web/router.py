from datetime import date

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.db import get_cursor
from app.models.aluno import Aluno
from app.models.treino import Treino
from app.models.exercicio import Exercicio
from app.models.exercicio_do_treino import ExercicioDoTreino


from app.services.alunos_service import  (
    list_alunos,
    get_aluno,
    create_aluno,
    update_aluno,
    delete_aluno,
)
from app.services.treinos_service import (
    list_treinos_with_aluno,
    create_treino,
    get_treino,
    update_treino,
    delete_treino,
)
from app.services.exercicios_service import (
    list_exercicios as service_list_exercicios,
    create_exercicio,
    get_exercicio,
    update_exercicio,
    delete_exercicio
)

from app.services.exercicios_treino_service import (
    list_exercicios_do_treino_service,
    create_exercicio_do_treino,
    update_exercicio_do_treino_service,
    delete_exercicio_do_treino_service,
    reorder_exercicios_do_treino_service,
    adicionar_exercicios_padrao_ao_treino_service
)

router = APIRouter(prefix="/web", tags=["web"])

# Caminho para os templates:
# daily_trainer/web/templates/...
templates = Jinja2Templates(directory="web/templates")

def get_db_cursor():
    from app.core.db import get_cursor as _get_cursor
    # Reuso do contextmanager do backend
    with _get_cursor() as cursor:
        yield cursor

# ---------- PÁGINA INICIAL ----------


@router.get("/", response_class=HTMLResponse)
def web_home(request: Request):
    """
    Página inicial da versão web do Daily Trainer.
    Apenas renderiza um dashboard simples (que vamos criar em home.html).
    """
    context = {
        "request": request,
        "titulo": "Daily Trainer - Web",
    }
    return templates.TemplateResponse("home.html", context)


# ---------- ALUNOS ----------

@router.get("/alunos", response_class=HTMLResponse)
def web_listar_alunos(
    request: Request,
    cursor=Depends(get_db_cursor),
):
    """
    Página com a lista de alunos.
    Usa o service list_alunos para compartilhar a mesma lógica da API.
    """
    alunos = list_alunos(cursor)

    context = {
        "request": request,
        "titulo": "Alunos",
        "alunos": alunos,
    }
    return templates.TemplateResponse("alunos/lista.html", context)

@router.get("/alunos/novo", response_class=HTMLResponse)
def web_novo_aluno(request: Request):
    """
    Exibe o formulário para cadastrar um novo aluno.
    """
    context = {
        "request": request,
        "titulo": "Novo Aluno",
        "modo": "novo",
        "aluno": None,
        "action_url": "/web/alunos/novo",
    }
    return templates.TemplateResponse("alunos/form.html", context)

@router.post("/alunos/novo")
def web_criar_aluno(
    request: Request,
    nome: str = Form(...),
    genero: str = Form(...),
    telefone: str = Form(""),
    turma: str = Form(""),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de novo aluno e cria via service.
    """
    aluno = Aluno(
        id=None,
        nome=nome,
        genero=genero,
        telefone=telefone or None,
        turma=turma or None,
        observacoes=observacoes or None,
    )
    create_aluno(cursor, aluno)
    return RedirectResponse(url="/web/alunos", status_code=303)

@router.get("/alunos/{aluno_id}/editar", response_class=HTMLResponse)
def web_editar_aluno(
    request: Request,
    aluno_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exibe o formulário para editar um aluno existente.
    """
    aluno = get_aluno(cursor, aluno_id)
    if not aluno:
        return RedirectResponse(url="/web/alunos", status_code=303)

    context = {
        "request": request,
        "titulo": f"Editar Aluno #{aluno.id}",
        "modo": "editar",
        "aluno": aluno,
        "action_url": f"/web/alunos/{aluno.id}/editar",
    }
    return templates.TemplateResponse("alunos/form.html", context)

@router.post("/alunos/{aluno_id}/editar")
def web_atualizar_aluno(
    request: Request,
    aluno_id: int,
    nome: str = Form(...),
    genero: str = Form(...),
    telefone: str = Form(""),
    turma: str = Form(""),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de edição e atualiza via service.
    """
    aluno = Aluno(
        id=aluno_id,
        nome=nome,
        genero=genero,
        telefone=telefone or None,
        turma=turma or None,
        observacoes=observacoes or None,
    )
    atualizado = update_aluno(cursor, aluno_id, aluno)
    if not atualizado:
        # Se sumiu no meio do caminho, só volta pra lista
        return RedirectResponse(url="/web/alunos", status_code=303)

    return RedirectResponse(url="/web/alunos", status_code=303)

@router.post("/alunos/{aluno_id}/deletar")
def web_deletar_aluno(
    aluno_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exclui o aluno e seus treinos vinculados.
    """
    delete_aluno(cursor, aluno_id)
    return RedirectResponse(url="/web/alunos", status_code=303)

# ---------- TREINOS ----------

@router.get("/treinos", response_class=HTMLResponse)
def web_listar_treinos(
    request: Request,
    cursor=Depends(get_db_cursor),
):
    """
    Página com a lista de treinos (sessões do dia).
    Usa o service list_treinos_with_aluno para compartilhar lógica com a API.
    """

    treinos_view = list_treinos_with_aluno(cursor)

    # Mapeia exercicios agrupados por grupo_muscular e prepara resumo para cada treino
    exercicios_por_treino = {}
    exercicios_resumo = {}
    alunos_lista = list_alunos(cursor)
    if treinos_view:
        treino_ids = [t["id"] for t in treinos_view]
        placeholders = ",".join(["?"] * len(treino_ids))
        cursor.execute(
            f"""
            SELECT
                edt.treino_id,
                COALESCE(NULLIF(TRIM(e.grupo_muscular), ''), 'Sem grupo') AS grupo,
                e.nome,
                e.apelido
            FROM exercicios_do_treino edt
            JOIN exercicios e ON e.id = edt.exercicio_id
            WHERE edt.treino_id IN ({placeholders})
            ORDER BY grupo, e.nome;
            """,
            treino_ids,
        )
        for treino_id, grupo, nome, apelido in cursor.fetchall():
            grupos = exercicios_por_treino.setdefault(treino_id, {})
            display_nome = nome
            if apelido:
                display_nome += f" ({apelido})"
            grupos.setdefault(grupo, []).append(display_nome)
        # Resumo: total de exercicios e grupos ordenados
        for treino_id, grupos in exercicios_por_treino.items():
            total = sum(len(nomes) for nomes in grupos.values())
            grupos_ordenados = sorted(grupos.items(), key=lambda x: x[0])
            exercicios_resumo[treino_id] = {
                "total": total,
                "grupos": grupos_ordenados,
            }

    context = {
            "request": request,
            "titulo": "Treinos",
            "treinos": treinos_view,
            "exercicios_por_treino": exercicios_por_treino,
            "exercicios_resumo": exercicios_resumo,
            "alunos_lista": alunos_lista,
    }
    return templates.TemplateResponse("treinos/lista.html", context)

@router.get("/treinos/novo", response_class=HTMLResponse)
def web_novo_treino(
    request: Request,
    cursor=Depends(get_db_cursor),
):
    """
    Exibe o formulário para cadastrar um novo treino (sessão do dia).
    """
    alunos = list_alunos(cursor)

    context = {
        "request": request,
        "titulo": "Novo Treino",
        "modo": "novo",
        "treino": None,
        "alunos": alunos,
        "action_url": "/web/treinos/novo",
    }
    return templates.TemplateResponse("treinos/form.html", context)

@router.post("/treinos/novo")
def web_criar_treino(
    request: Request,
    aluno_id: int = Form(...),
    data: str = Form(...),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de novo treino e cria via service.
    """

    data_obj = date.fromisoformat(data)

    treino = Treino(
        id=None,
        aluno_id=aluno_id,
        data=data_obj,
        observacoes=observacoes or None,
    )

    novo = create_treino(cursor, treino)
    return RedirectResponse(url=f"/web/treinos/{novo.id}", status_code=303)

@router.get("/treinos/{treino_id}", response_class=HTMLResponse)
def web_detalhe_treino(
    request: Request,
    treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Tela de detalhe do treino:
    - Info do treino + aluno
    - Lista de exercícios do treino
    - Formulários para adicionar exercícios padrão ou manuais
    """

    # Buscar treino + nome do aluno
    cursor.execute(
        """
        SELECT t.id, t.aluno_id, t.data, t.observacoes, a.nome, a.genero
        FROM treinos t
        JOIN alunos a ON a.id = t.aluno_id
        WHERE t.id = ?;
        """,
        [treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return RedirectResponse(url="/web/treinos", status_code=303)

    treino_view = {
        "id": row[0],
        "aluno_id": row[1],
        "data": row[2],
        "observacoes": row[3],
        "aluno_nome": row[4],
        "aluno_genero": row[5],
    }




    # Exercícios do treino (com info do catálogo)
    cursor.execute(
        """
        SELECT
            edt.id,
            edt.ordem,
            edt.exercicio_id,
            e.nome,
            e.apelido,
            e.grupo_muscular,
            edt.series,
            edt.repeticoes,
            edt.carga,
            edt.observacoes
        FROM exercicios_do_treino edt
        JOIN exercicios e ON e.id = edt.exercicio_id
        WHERE edt.treino_id = ?
        ORDER BY edt.ordem, edt.id;
        """,
        [treino_id],
    )
    rows = cursor.fetchall()
    exercicios_treino = [
        {
            "id": r[0],
            "ordem": r[1],
            "exercicio_id": r[2],
            "nome": r[3],
            "apelido": r[4],
            "grupo_muscular": r[5],
            "series": r[6],
            "repeticoes": r[7],
            "carga": r[8],
            "observacoes": r[9],
        }
        for r in rows
    ]

    grupos_resumo = {}
    for e in exercicios_treino:
        nome_grupo = e["grupo_muscular"] or "Sem grupo"
        grupos_resumo[nome_grupo] = grupos_resumo.get(nome_grupo, 0) + 1

    # Grupos musculares disponiveis para exercicios padrao conforme genero do aluno
    grupos_padrao = []
    genero_aluno = treino_view["aluno_genero"]
    if genero_aluno == "unissex":
        cursor.execute(
            """
            SELECT DISTINCT lower(grupo_muscular)
            FROM exercicios
            WHERE padrao = TRUE
              AND publico_alvo = 'unissex'
              AND grupo_muscular IS NOT NULL
              AND TRIM(grupo_muscular) <> '';
            """
        )
    else:
        cursor.execute(
            """
            SELECT DISTINCT lower(grupo_muscular)
            FROM exercicios
            WHERE padrao = TRUE
              AND publico_alvo IN (?, 'unissex')
              AND grupo_muscular IS NOT NULL
              AND TRIM(grupo_muscular) <> '';
            """,
            [genero_aluno],
        )
    grupos_padrao = sorted([row[0] for row in cursor.fetchall()])

    alunos_lista = list_alunos(cursor)

    # Exercícios disponíveis no catálogo (para adicionar manualmente)
    exercicios_catalogo = service_list_exercicios(cursor, genero=None)

    context = {
        "request": request,
        "titulo": f"Treino #{treino_view['id']}",
        "treino": treino_view,
        "exercicios_treino": exercicios_treino,
        "exercicios_catalogo": exercicios_catalogo,
        "perfis": ["leve", "moderado", "intenso"],
        "total_exercicios": len(exercicios_treino),
        "grupos_resumo": grupos_resumo,
        "alunos_lista": alunos_lista,
        "grupos_padrao": grupos_padrao,
    }
    return templates.TemplateResponse("treinos/detalhe.html", context)

@router.post("/treinos/{treino_id}/exercicios/adicionar_padrao")
def web_adicionar_exercicios_padrao_ao_treino(
    treino_id: int,
    grupo_muscular: str = Form(...),
    perfil: str = Form("moderado"),
    cursor=Depends(get_db_cursor),
):
    """
    Adiciona exercícios padrão de um grupo muscular ao treino (via service).
    """

    resultado = adicionar_exercicios_padrao_ao_treino_service(
        cursor, treino_id, grupo_muscular, perfil
    )

    # Se treino/aluno não encontrado
    if resultado is None:
        # Volta pra lista de treinos
        return RedirectResponse(url="/web/treinos", status_code=303)

    # Mesmo se lista vazia, só recarrega a página de detalhe
    return RedirectResponse(
        url=f"/web/treinos/{treino_id}",
        status_code=303,
    )

@router.get("/treinos/{treino_id}/editar", response_class=HTMLResponse)
def web_editar_treino(
    request: Request,
    treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exibe o formulário para editar um treino existente.
    """

    treino = get_treino(cursor, treino_id)
    if not treino:
        return RedirectResponse(url="/web/treinos", status_code=303)

    alunos = list_alunos(cursor)

    context = {
        "request": request,
        "titulo": f"Editar Treino #{treino.id}",
        "modo": "editar",
        "treino": treino,
        "alunos": alunos,
        "action_url": f"/web/treinos/{treino.id}/editar",
    }
    return templates.TemplateResponse("treinos/form.html", context)

@router.post("/treinos/{treino_id}/editar")
def web_atualizar_treino(
    request: Request,
    treino_id: int,
    aluno_id: int = Form(...),
    data: str = Form(...),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de edição e atualiza o treino via service.
    """

    data_obj = date.fromisoformat(data)

    treino = Treino(
        id=treino_id,
        aluno_id=aluno_id,
        data=data_obj,
        observacoes=observacoes or None,
    )

    atualizado = update_treino(cursor, treino_id, treino)
    if not atualizado:
        return RedirectResponse(url="/web/treinos", status_code=303)

    return RedirectResponse(url="/web/treinos", status_code=303)

@router.post("/treinos/{treino_id}/deletar")
def web_deletar_treino(
    treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exclui o treino e seus exercícios vinculados.
    """
    delete_treino(cursor, treino_id)
    return RedirectResponse(url="/web/treinos", status_code=303)

@router.post("/treinos/{treino_id}/exercicios/adicionar")
def web_adicionar_exercicio_ao_treino(
    treino_id: int,
    exercicio_id: int = Form(...),
    series: int = Form(...),
    repeticoes: int = Form(...),
    carga: str = Form(""),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Adiciona um exercício específico do catálogo ao treino.
    """

    carga_val = float(carga) if carga else None

    exercicio_treino = ExercicioDoTreino(
        id=None,
        treino_id=treino_id,
        exercicio_id=exercicio_id,
        series=series,
        repeticoes=repeticoes,
        carga=carga_val,
        observacoes=observacoes or None,
    )

    create_exercicio_do_treino(cursor, treino_id, exercicio_treino)

    return RedirectResponse(
        url=f"/web/treinos/{treino_id}",
        status_code=303,
    )

@router.get("/treinos/{treino_id}/exercicios/{exercicio_treino_id}/editar", response_class=HTMLResponse)
def web_editar_exercicio_do_treino(
    request: Request,
    treino_id: int,
    exercicio_treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exibe formulário para editar um exercício dentro do treino.
    """

    cursor.execute(
        """
        SELECT
            edt.id,
            edt.treino_id,
            edt.exercicio_id,
            e.nome,
            e.apelido,
            edt.series,
            edt.repeticoes,
            edt.carga,
            edt.observacoes
        FROM exercicios_do_treino edt
        JOIN exercicios e ON e.id = edt.exercicio_id
        WHERE edt.id = ? AND edt.treino_id = ?;
        """,
        [exercicio_treino_id, treino_id],
    )
    row = cursor.fetchone()
    if not row:
        return RedirectResponse(url=f"/web/treinos/{treino_id}", status_code=303)

    exercicio_view = {
        "id": row[0],
        "treino_id": row[1],
        "exercicio_id": row[2],
        "nome": row[3],
        "apelido": row[4],
        "series": row[5],
        "repeticoes": row[6],
        "carga": row[7],
        "observacoes": row[8],
    }

    context = {
        "request": request,
        "titulo": f"Editar Exercício do Treino #{treino_id}",
        "exercicio_treino": exercicio_view,
        "action_url": f"/web/treinos/{treino_id}/exercicios/{exercicio_treino_id}/editar",
    }
    return templates.TemplateResponse("treinos/editar_exercicio.html", context)

@router.post("/treinos/{treino_id}/exercicios/{exercicio_treino_id}/editar")
def web_atualizar_exercicio_do_treino(
    treino_id: int,
    exercicio_treino_id: int,
    series: int = Form(...),
    repeticoes: int = Form(...),
    carga: str = Form(""),
    observacoes: str = Form(""),
    cursor=Depends(get_db_cursor),
):
    """
    Atualiza séries, repetições, carga e observações de um exercício do treino.
    """

    carga_val = float(carga) if carga else None

    # Obter exercicio_id atual
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
        return RedirectResponse(url=f"/web/treinos/{treino_id}", status_code=303)

    exercicio_id = row[0]

    exercicio_treino_model = ExercicioDoTreino(
        id=exercicio_treino_id,
        treino_id=treino_id,
        exercicio_id=exercicio_id,
        series=series,
        repeticoes=repeticoes,
        carga=carga_val,
        observacoes=observacoes or None,
    )

    atualizado = update_exercicio_do_treino_service(
        cursor, treino_id, exercicio_treino_id, exercicio_treino_model
    )
    # Se algo der errado, apenas volta pra página do treino
    return RedirectResponse(
        url=f"/web/treinos/{treino_id}",
        status_code=303,
    )

@router.post("/treinos/{treino_id}/exercicios/{exercicio_treino_id}/mover")
def web_mover_exercicio_do_treino(
    treino_id: int,
    exercicio_treino_id: int,
    direcao: str = Form(...),  # "up" ou "down"
    cursor=Depends(get_db_cursor),
):
    """
    Move um exercício uma posição para cima ou para baixo na ordem.
    Usa o service de reorder.
    """

    # Buscar lista atual ordenada
    lista = list_exercicios_do_treino_service(cursor, treino_id)
    ids = [e.id for e in lista]
    if exercicio_treino_id not in ids:
        return RedirectResponse(
            url=f"/web/treinos/{treino_id}",
            status_code=303,
        )

    idx = ids.index(exercicio_treino_id)
    if direcao == "up" and idx > 0:
        ids[idx - 1], ids[idx] = ids[idx], ids[idx - 1]
    elif direcao == "down" and idx < len(ids) - 1:
        ids[idx + 1], ids[idx] = ids[idx], ids[idx + 1]

    reorder_exercicios_do_treino_service(cursor, treino_id, ids)

    return RedirectResponse(
        url=f"/web/treinos/{treino_id}",
        status_code=303,
    )

@router.post("/treinos/{treino_id}/exercicios/{exercicio_treino_id}/deletar")
def web_deletar_exercicio_do_treino(
    treino_id: int,
    exercicio_treino_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Remove um exercício do treino.
    """
    delete_exercicio_do_treino_service(cursor, treino_id, exercicio_treino_id)
    return RedirectResponse(
        url=f"/web/treinos/{treino_id}",
        status_code=303,
    )


# ---------- EXERCÍCIOS ----------


@router.get("/exercicios", response_class=HTMLResponse)
def web_listar_exercicios(
    request: Request,
    cursor=Depends(get_db_cursor),
):
    """
    Página com a lista de exercícios do catálogo.
    Usa o service list_exercicios (sem filtro de gênero).
    """

    exercicios = service_list_exercicios(cursor, genero=None)

    context = {
        "request": request,
        "titulo": "Exercícios",
        "exercicios": exercicios,
    }
    return templates.TemplateResponse("exercicios/lista.html", context)

@router.get("/exercicios/novo", response_class=HTMLResponse)
def web_novo_exercicio(request: Request):
    """
    Exibe o formulário para cadastrar um novo exercício.
    """
    context = {
        "request": request,
        "titulo": "Novo Exercício",
        "modo": "novo",
        "exercicio": None,
        "action_url": "/web/exercicios/novo",
    }
    return templates.TemplateResponse("exercicios/form.html", context)

@router.post("/exercicios/novo")
def web_criar_exercicio(
    request: Request,
    nome: str = Form(...),
    apelido: str = Form(""),
    grupo_muscular: str = Form(""),
    descricao: str = Form(""),
    series_padrao: int = Form(...),
    repeticoes_padrao: int = Form(...),
    publico_alvo: str = Form(...),
    padrao: bool = Form(False),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de novo exercício e cria via service.
    """

    exercicio = Exercicio(
        id=None,
        nome=nome,
        apelido=apelido or None,
        grupo_muscular=grupo_muscular or None,
        descricao=descricao or None,
        series_padrao=series_padrao,
        repeticoes_padrao=repeticoes_padrao,
        publico_alvo=publico_alvo,
        padrao=padrao,
    )

    create_exercicio(cursor, exercicio)
    return RedirectResponse(url="/web/exercicios", status_code=303)

@router.get("/exercicios/{exercicio_id}/editar", response_class=HTMLResponse)
def web_editar_exercicio(
    request: Request,
    exercicio_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exibe o formulário para editar um exercício existente.
    """
    exercicio = get_exercicio(cursor, exercicio_id)
    if not exercicio:
        return RedirectResponse(url="/web/exercicios", status_code=303)

    context = {
        "request": request,
        "titulo": f"Editar Exercício #{exercicio.id}",
        "modo": "editar",
        "exercicio": exercicio,
        "action_url": f"/web/exercicios/{exercicio.id}/editar",
    }
    return templates.TemplateResponse("exercicios/form.html", context)

@router.post("/exercicios/{exercicio_id}/editar")
def web_atualizar_exercicio(
    request: Request,
    exercicio_id: int,
    nome: str = Form(...),
    apelido: str = Form(""),
    grupo_muscular: str = Form(""),
    descricao: str = Form(""),
    series_padrao: int = Form(...),
    repeticoes_padrao: int = Form(...),
    publico_alvo: str = Form(...),
    padrao: bool = Form(False),
    cursor=Depends(get_db_cursor),
):
    """
    Recebe o formulário de edição e atualiza via service.
    """

    exercicio = Exercicio(
        id=exercicio_id,
        nome=nome,
        apelido=apelido or None,
        grupo_muscular=grupo_muscular or None,
        descricao=descricao or None,
        series_padrao=series_padrao,
        repeticoes_padrao=repeticoes_padrao,
        publico_alvo=publico_alvo,
        padrao=padrao,
    )

    atualizado = update_exercicio(cursor, exercicio_id, exercicio)
    if not atualizado:
        return RedirectResponse(url="/web/exercicios", status_code=303)

    return RedirectResponse(url="/web/exercicios", status_code=303)

@router.post("/exercicios/{exercicio_id}/deletar")
def web_deletar_exercicio(
    exercicio_id: int,
    cursor=Depends(get_db_cursor),
):
    """
    Exclui o exercício do catálogo e suas referências em treinos.
    """
    delete_exercicio(cursor, exercicio_id)
    return RedirectResponse(url="/web/exercicios", status_code=303)

