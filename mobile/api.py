import sys
from pathlib import Path

# Garante que o pacote "app" do backend esteja no sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.core.db import get_cursor  # type: ignore
from app.services.alunos_service import list_alunos as svc_list_alunos  # type: ignore
from app.services.treinos_service import list_treinos as svc_list_treinos  # type: ignore
from app.services.exercicios_service import list_exercicios as svc_list_exercicios  # type: ignore
from app.services.exercicios_treino_service import (
    list_exercicios_do_treino_service as svc_list_edt,
)  # type: ignore
from datetime import date


def list_alunos():
    with get_cursor() as cursor:
        return svc_list_alunos(cursor)


def list_treinos():
    with get_cursor() as cursor:
        return svc_list_treinos(cursor)


def list_exercicios():
    with get_cursor() as cursor:
        return svc_list_exercicios(cursor, genero=None)


def dashboard_summary():
    hoje = date.today()
    with get_cursor() as cursor:
        alunos = svc_list_alunos(cursor)
        treinos = svc_list_treinos(cursor)

        # Alunos sem treino hoje
        alunos_sem = []
        treinos_hoje = [t for t in treinos if t.data == hoje]
        treinos_hoje_by_aluno = {}
        for t in treinos_hoje:
            treinos_hoje_by_aluno.setdefault(t.aluno_id, []).append(t)

        for a in alunos:
            if a.id not in treinos_hoje_by_aluno:
                alunos_sem.append(a)

        # Treinos do dia + grupos
        treinos_resumo = []
        for t in treinos_hoje:
            grupos = set()
            try:
                edt_list = svc_list_edt(cursor, t.id)
                for edt in edt_list:
                    # precisamos do nome do grupo: buscar do catalogo
                    cursor.execute(
                        "SELECT grupo_muscular FROM exercicios WHERE id = ?;",
                        [edt.exercicio_id],
                    )
                    row = cursor.fetchone()
                    grupo = row[0] if row and row[0] else "Sem grupo"
                    grupos.add(grupo)
            except Exception:
                pass
            treinos_resumo.append(
                {
                    "treino_id": t.id,
                    "aluno_id": t.aluno_id,
                    "data": t.data,
                    "grupos": sorted(grupos),
                }
            )

        return alunos_sem, treinos_resumo
