from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.competitions import router as competitions_router
from app.api.routes.criteria import router as criteria_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.judge_votes import router as judge_votes_router
from app.api.routes.judges import router as judges_router
from app.api.routes.participants import router as participants_router
from app.api.routes.public_votes import router as public_votes_router
from app.api.routes.results import router as results_router
from app.api.routes.voting_sessions import router as voting_sessions_router
from app.config import get_settings
from app.services.access_service import JudgeAccessError
from app.services.admin_service import ResourceNotFound
from app.services.judge_vote_service import JudgeVoteError
from app.services.public_vote_service import PublicVoteError
from app.services.voting_service import VotingStateError


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

    @app.exception_handler(VotingStateError)
    async def voting_state_error_handler(
        _request: Request,
        exc: VotingStateError,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(PublicVoteError)
    async def public_vote_error_handler(
        _request: Request,
        exc: PublicVoteError,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(JudgeAccessError)
    async def judge_access_error_handler(
        _request: Request,
        exc: JudgeAccessError,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(JudgeVoteError)
    async def judge_vote_error_handler(
        _request: Request,
        exc: JudgeVoteError,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(competitions_router)
    app.include_router(participants_router)
    app.include_router(criteria_router)
    app.include_router(judges_router)
    app.include_router(judge_votes_router)
    app.include_router(voting_sessions_router)
    app.include_router(public_votes_router)
    app.include_router(results_router)
    return app


app = create_app()
