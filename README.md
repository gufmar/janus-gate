# Janus Gate

Janus Gate is a bidirectional Cardano API compatibility gateway. Named after the two-faced Roman god, each instance presents one public API face (Blockfrost or Koios) and fulfills requests by querying the other provider on the backend.

This is not a 1:1 reverse proxy. Paths, HTTP methods, field names, and shapes are translated so a client can keep talking Blockfrost while data comes from Koios (or the reverse).

## Status

Proof of concept. Covered endpoints:

| Concept | Blockfrost face | Koios face |
| --- | --- | --- |
| Network tip / latest block | `GET /blocks/latest` | `GET /tip` |
| Address info | `GET /addresses/{address}` | `POST /address_info` |

Plus Janus-native `GET /health` for probes.

See [docs/architecture.md](docs/architecture.md), [docs/api-comparison/overview.md](docs/api-comparison/overview.md), and the full triage map in [docs/api-comparison/endpoint-catalog.md](docs/api-comparison/endpoint-catalog.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quickstart

```bash
uv sync
cp config.example.yaml config.yaml
cp .env.example .env
# set JANUS_BACKEND_API_KEY in .env when the upstream requires it
uv run janus-gate validate-config --config config.yaml
uv run janus-gate serve --config config.yaml
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Example Blockfrost-face tip (with `public_face: blockfrost` and Koios backend):

```bash
curl http://127.0.0.1:8080/blocks/latest
```

Swap faces in `config.yaml` (`public_face: koios`, `backend.provider: blockfrost`) to expose Koios-shaped routes backed by Blockfrost. See also `config.koios-face.example.yaml` (Blockfrost backend needs `JANUS_BACKEND_API_KEY`).

## CLI

```bash
uv run janus-gate version
uv run janus-gate validate-config --config config.yaml
uv run janus-gate serve --config config.yaml [--host 0.0.0.0] [--port 8080]
```

## systemd

A unit file lives at [deploy/janus-gate.service](deploy/janus-gate.service). Install the project under `/opt/janus-gate`, place `config.yaml` and `.env`, then enable the unit.

## nginx

Janus Gate speaks plain HTTP. Put nginx (or another reverse proxy) in front for TLS, public auth, rate limits, and buffering. Point the upstream at Janus Gate's listen address (default `0.0.0.0:8080`, or bind to localhost only in production).

## License

Apache License 2.0. See [LICENSE](LICENSE).
