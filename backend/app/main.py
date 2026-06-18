from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.competitions import router as competitions_router
from app.api.routes.criteria import router as criteria_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.judges import router as judges_router
from app.api.routes.participants import router as participants_router
from app.config import get_settings
from app.services.admin_service import ResourceNotFound


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    origins = [
        origin.strip()
        for origin in settings.backend_cors_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ResourceNotFound)
    async def resource_not_found_handler(
        _request: Request,
        exc: ResourceNotFound,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": f"{exc.resource} not found"},
        )

    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(competitions_router)
    app.include_router(participants_router)
    app.include_router(criteria_router)
    app.include_router(judges_router)
    return app


app = create_app()
