from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, boards, cards, lists
from app.config import get_settings
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Kanban API", version="1.0.0")

    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (auth.router, boards.router, lists.router, cards.router):
        app.include_router(router, prefix="/api")

    return app


app = create_app()
