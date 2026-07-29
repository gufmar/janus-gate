"""Janus Gate command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import uvicorn

from janus_gate import __version__
from janus_gate.app import create_app
from janus_gate.config import load_config

app = typer.Typer(
    name="janus-gate",
    help="Bidirectional Cardano API compatibility gateway (Blockfrost <-> Koios).",
    no_args_is_help=True,
)


def _resolve_config(config: Optional[Path]) -> Path | None:
    if config is not None:
        return config
    default = Path("config.yaml")
    if default.is_file():
        return default
    example = Path("config.example.yaml")
    if example.is_file():
        return example
    return None


@app.command("version")
def version_cmd() -> None:
    """Print the Janus Gate version."""
    typer.echo(__version__)


@app.command("validate-config")
def validate_config(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML config file.",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Load and validate configuration."""
    path = _resolve_config(config)
    if path is None and config is None:
        raise typer.BadParameter(
            "No config file found. Pass --config or create config.yaml."
        )
    try:
        loaded = load_config(path)
    except Exception as exc:
        typer.secho(f"Invalid config: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho("Config OK", fg=typer.colors.GREEN)
    typer.echo(f"  public_face: {loaded.public_face.value}")
    typer.echo(f"  backend:     {loaded.backend.provider.value}")
    typer.echo(f"  base_url:    {loaded.backend.base_url}")
    typer.echo(f"  listen:      {loaded.server.host}:{loaded.server.port}")
    typer.echo(f"  base_path:   {loaded.server.base_path or '/'}")
    typer.echo(f"  key_map:     {len(loaded.auth.key_map)} entr(y/ies)")
    typer.echo(
        "  fallback:    "
        + (
            "anonymous upstream"
            if not loaded.auth.fallback_backend_key
            else "set"
        )
    )
    typer.echo(
        f"  api_key:     {'set' if loaded.backend.api_key else 'not set'} (legacy backend.api_key)"
    )


@app.command("serve")
def serve(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML config file.",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        help="Override listen host.",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        help="Override listen port.",
    ),
) -> None:
    """Start the Janus Gate HTTP service (plain HTTP; put nginx in front)."""
    path = _resolve_config(config)
    if path is None and config is None:
        raise typer.BadParameter(
            "No config file found. Pass --config or create config.yaml."
        )
    try:
        loaded = load_config(path)
    except Exception as exc:
        typer.secho(f"Invalid config: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if host:
        loaded.server.host = host
    if port is not None:
        loaded.server.port = port

    fastapi_app = create_app(loaded)
    uvicorn.run(
        fastapi_app,
        host=loaded.server.host,
        port=loaded.server.port,
        root_path=loaded.server.base_path,
        log_level="info",
    )


if __name__ == "__main__":
    app()
