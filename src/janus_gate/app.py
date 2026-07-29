"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from janus_gate import __version__
from janus_gate.auth import (
    ApiKeyMappingMiddleware,
    auth_health_payload,
    configure_auth_fallback,
)
from janus_gate.config import AppConfig, ProviderName, public_url
from janus_gate.faces.blockfrost import build_blockfrost_router
from janus_gate.faces.errors import register_face_exception_handlers
from janus_gate.faces.koios import build_koios_router
from janus_gate.pages import render_endpoints_html
from janus_gate.providers import create_backend


def create_app(config: AppConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_auth_fallback(config.auth.fallback_backend_key)
        backend = create_backend(config)
        app.state.backend = backend
        app.state.config = config
        try:
            yield
        finally:
            await backend.aclose()

    app = FastAPI(
        title="Janus Gate",
        version=__version__,
        description=(
            "Bidirectional Cardano API compatibility gateway. "
            "TLS and public auth are expected from a reverse proxy such as nginx."
        ),
        root_path=config.server.base_path,
        lifespan=lifespan,
    )
    app.add_middleware(ApiKeyMappingMiddleware, config=config)
    register_face_exception_handlers(app, config.public_face)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "public_face": config.public_face.value,
            "backend": config.backend.provider.value,
            "base_path": config.server.base_path or "/",
            "endpoints": public_url(config.server.base_path, "/endpoints"),
            "auth": auth_health_payload(config.auth),
        }

    @app.get("/endpoints", response_class=HTMLResponse, include_in_schema=False)
    async def endpoints_page() -> str:
        return render_endpoints_html(
            public_face=config.public_face,
            backend=config.backend.provider,
            base_path=config.server.base_path,
        )

    if config.public_face is ProviderName.BLOCKFROST:
        app.include_router(build_blockfrost_router())
    elif config.public_face is ProviderName.KOIOS:
        app.include_router(build_koios_router())
    else:
        raise ValueError(f"Unsupported public face: {config.public_face}")

    return app
