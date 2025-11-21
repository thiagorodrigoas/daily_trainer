from functools import lru_cache
from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

class Settings:
    def __init__(self):
        self.APP_NAME = os.getenv("APP_NAME", "Daily Trainer")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.DB_PATH = os.getenv("DUCKDB_PATH", "app/db/data/daily_trainer.duckdb")


@lru_cache
def get_settings() -> Settings:
    """
    Retorna uma única instância de Settings (singleton).
    As variáveis do .env já ficam carregadas.
    """
    return Settings()
