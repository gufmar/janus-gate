# Janus Gate

Janus Gate is a bidirectional Cardano API compatibility gateway. Named after the two-faced Roman god, each instance presents one public API face (Blockfrost or Koios) and fulfills requests by querying the other provider on the backend.

This is not a 1:1 reverse proxy. Paths, HTTP methods, field names, and shapes are translated so a client can keep talking Blockfrost while data comes from Koios (or the reverse).

## Status

Proof of concept expanding the catalog **Likely** band. Covered endpoints:

| Concept | Blockfrost face | Koios face |
| --- | --- | --- |
| Network tip / latest block | `GET /blocks/latest` | `GET /tip` |
| Block by hash/height | `GET /blocks/{hash_or_number}` | `POST /block_info` |
| Genesis | `GET /genesis` | `GET /genesis` |
| Epoch info | `GET /epochs/latest`, `/epochs/{number}` | `GET /epoch_info` |
| Epoch parameters | `GET /epochs/.../parameters` | `GET /epoch_params` |
| Transaction | `GET /txs/{hash}` (+ utxos/metadata/cbor) | `POST /tx_info` (+ utxos/metadata/cbor) |
| Address info | `GET /addresses/{address}` | `POST /address_info` |
| Address UTxOs | `GET /addresses/{address}/utxos` | `POST /address_utxos` |
| Address transactions | `GET /addresses/{address}/transactions` | `POST /address_txs` |
| Account info | `GET /accounts/{stake_address}` | `POST /account_info` |
| Pools | `GET /pools`, `/pools/extended`, `/pools/{id}` | `GET /pool_list`, `POST /pool_info` |
| Asset info | `GET /assets/{asset}` | `POST /asset_info` |
| Submit transaction | `POST /tx/submit` | `POST /submittx` |

Plus Janus-native `GET /health` for probes and `GET /endpoints` for an HTML coverage overview (implemented routes are linked).

See [docs/architecture.md](docs/architecture.md), [docs/api-comparison/overview.md](docs/api-comparison/overview.md), and the full triage map in [docs/api-comparison/endpoint-catalog.md](docs/api-comparison/endpoint-catalog.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## System packages

On Debian/Ubuntu (typical VM), install the OS packages below before `uv sync`:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip curl ca-certificates
```

Then install `uv` (official installer):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The installer places `uv` in `~/.local/bin` by default. Make sure that directory is on your `PATH`, then verify:

```bash
uv --version
```

### PATH on Debian (bash)

`PATH` is not usually set in one global file for your user tools. On a typical Debian bash setup:

| File | When it runs |
| --- | --- |
| `~/.profile` | Login shells (common for SSH sessions). Debian’s default here already prepends `~/.local/bin` and `~/bin` when those dirs exist. |
| `~/.bashrc` | Interactive non-login bash shells (new terminal tabs, `bash` without login). Often sourced from `~/.profile` when bash is the login shell. |
| `/etc/environment` or `/etc/profile` | System-wide; prefer user files for `uv`. |

If `uv` is installed but `uv: command not found`, check which shell file is active and that `~/.local/bin` is included.

**Option A – rely on Debian’s default `~/.profile` (recommended)**

Confirm these lines exist (stock Debian images usually already have them):

```bash
# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
```

Then either open a new SSH login session, or reload:

```bash
source ~/.profile
```

**Option B – also add it in `~/.bashrc` (handy for non-login interactive shells)**

```bash
# ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
```

Reload with `source ~/.bashrc`, or open a new shell.

**Quick checks**

```bash
echo "$PATH"
which uv
ls -l "$HOME/.local/bin/uv"
```

**systemd note:** service units do not load `~/.profile` or `~/.bashrc`. Prefer a full path in `ExecStart` (for example `/home/<user>/.local/bin/uv run ...`) or set `Environment=PATH=...` / an `EnvironmentFile` in the unit. See [deploy/janus-gate.service](deploy/janus-gate.service).

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

Swap faces in `config.yaml` (`public_face: koios`, `backend.provider: blockfrost`) to expose Koios-shaped routes backed by Blockfrost. See also `config.koios-face.example.yaml` (Blockfrost backend needs a mapped or fallback API key).

## API key mapping

Clients authenticate with the **public face** header style:

- Blockfrost face: `project_id: <public_key>`
- Koios face: `Authorization: Bearer <public_key>`

Janus looks up that key in `auth.key_map` and uses the mapped `backend_key` for upstream calls. Unknown or missing public keys use `auth.fallback_backend_key` (omit/null/empty = anonymous upstream, e.g. Koios free tier). Fallback usage is logged and returned as `X-Janus-Auth-Warning`.

```yaml
auth:
  key_map:
    - label: tenant-a
      public_key: mainnetYourBlockfrostProjectId
      backend_key: your_koios_bearer_token
  fallback_backend_key: null
```

`GET /health` includes masked previews (`first10...last10`) of configured backend keys under `auth`.

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

If the public URL is under a subpath (for example `https://example.com/janus/...`) and nginx strips `/janus` before proxying, set the same prefix in config so HTML links and OpenAPI root-path stay correct:

```yaml
server:
  base_path: /janus
```

Or via env: `JANUS_BASE_PATH=/janus`.

## License

Apache License 2.0. See [LICENSE](LICENSE).
