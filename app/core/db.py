from contextlib import contextmanager
from pathlib import Path
import duckdb

from .config import get_settings

settings = get_settings()

# DuckDB recebe caminho como string, mas criamos pasta via Path
DB_PATH = Path(settings.DB_PATH).resolve()
# DB_PATH = Path(settings.DB_PATH)

# Conexão global (um por processo)
_connection = None

# Garante que a pasta existe
if DB_PATH.parent != Path("."):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    conn = duckdb.connect(str(DB_PATH))
    cursor = conn.cursor()

    # SEQUENCES
    cursor.execute("CREATE SEQUENCE IF NOT EXISTS alunos_seq START 1;")
    cursor.execute("CREATE SEQUENCE IF NOT EXISTS treinos_seq START 1;")
    cursor.execute("CREATE SEQUENCE IF NOT EXISTS exercicios_seq START 1;")
    cursor.execute("CREATE SEQUENCE IF NOT EXISTS exercicios_do_treino_seq START 1;")

    # Tabela de alunos
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            genero TEXT NOT NULL,
            telefone TEXT,
            turma TEXT,
            observacoes TEXT,
            CONSTRAINT chk_alunos_genero
                CHECK (genero IN ('masculino', 'feminino', 'unissex'))
        );
        """
    )

    # Tabela de treinos (sessão do dia)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS treinos (
            id INTEGER PRIMARY KEY,
            aluno_id INTEGER NOT NULL,
            data DATE NOT NULL,
            observacoes TEXT,
            CONSTRAINT fk_treinos_alunos
                FOREIGN KEY (aluno_id)
                REFERENCES alunos(id)
        );
        """
    )

    # Tabela de exercícios (catálogo)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exercicios (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            apelido TEXT,
            grupo_muscular TEXT,
            descricao TEXT,
            publico_alvo TEXT NOT NULL DEFAULT 'unissex',
            padrao BOOLEAN NOT NULL DEFAULT FALSE,
            series_padrao INTEGER NOT NULL DEFAULT 3,
            repeticoes_padrao INTEGER NOT NULL DEFAULT 10,
            CONSTRAINT chk_exercicios_publico_alvo
                CHECK (publico_alvo IN ('masculino', 'feminino', 'unissex'))
        );
        """
    )

    # Tabela de exercícios realizados em cada treino
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exercicios_do_treino (
            id INTEGER PRIMARY KEY,
            treino_id INTEGER NOT NULL,
            exercicio_id INTEGER NOT NULL,
            ordem INTEGER DEFAULT 0,
            series INTEGER NOT NULL,
            repeticoes INTEGER NOT NULL,
            carga DOUBLE,
            observacoes TEXT,
            CONSTRAINT fk_ex_treino_treinos
                FOREIGN KEY (treino_id)
                REFERENCES treinos(id),
            CONSTRAINT fk_ex_treino_exercicios
                FOREIGN KEY (exercicio_id)
                REFERENCES exercicios(id)
        );
        """
    )

    conn.commit()
    conn.close()

def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Retorna uma conexão global com o DuckDB.
    Garante que só abrimos o arquivo uma vez por processo.
    """
    global _connection
    if _connection is None:
        _connection = duckdb.connect(str(DB_PATH))
    return _connection

@contextmanager
def get_cursor():
    """
    Context manager que fornece um cursor a partir da conexão global.

    Uso:
        with get_cursor() as cursor:
            cursor.execute("...")
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    finally:
        cursor.close()