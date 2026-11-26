import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, correlation_id_var, get_logger, request_id_var
from app.workers.job_worker import background_worker
from app.services.neo4j import ensure_neo4j_schema, neo4j_manager

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("reconx.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_neo4j_schema()
    if settings.worker_enabled:
        background_worker.start()
    try:
        yield
    finally:
        if settings.worker_enabled:
            background_worker.stop()
        neo4j_manager.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        req_id = str(uuid4())
        corr_token = correlation_id_var.set(corr_id)
        req_token = request_id_var.set(req_id)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Correlation-ID"] = corr_id
            response.headers["X-Request-ID"] = req_id
            logger.info(
                "http_request",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    }
                },
            )
            return response
        finally:
            correlation_id_var.reset(corr_token)
            request_id_var.reset(req_token)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
