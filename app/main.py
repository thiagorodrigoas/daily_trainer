from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db import init_db
# from app.api.v1 import alunos as alunos_router
# from app.api.v1 import exercicios as exercicios_router
# from app.api.v1 import treinos as treinos_router

from web.router import router as web_router
settings = get_settings()

app = FastAPI(title=settings.APP_NAME)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "app": settings.APP_NAME,
    }


# app.include_router(alunos_router.router)
# app.include_router(exercicios_router.router)
# app.include_router(treinos_router.router)

app.include_router(web_router)
