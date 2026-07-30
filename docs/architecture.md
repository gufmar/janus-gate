# Architecture

## Role

Janus Gate sits between Cardano API clients and an upstream provider. Clients see a familiar public surface (Blockfrost or Koios). Janus fetches data from the configured backend provider, then maps paths, methods, and JSON fields into the public contract.

TLS, certificates, and edge HTTP concerns belong to nginx (or similar) in front of Janus. The service itself listens on plain HTTP.

## Request flow

```text
Client -> nginx (TLS) -> Janus Gate (face router) -> mapper -> backend client -> upstream API
                                                              <- mapped JSON <-
```

1. Client calls a face-compatible path (for example Blockfrost `GET /blocks/latest`).
2. Only routes for the configured `public_face` are mounted.
3. The mapper picks the equivalent backend call and transforms the payload.
4. The backend client authenticates to the upstream (Blockfrost `project_id`, Koios `Authorization: Bearer`).
5. The mapped response is returned to the client.

## Configuration

`public_face` and `backend.provider` must differ. Same-face passthrough is out of scope for this PoC; Janus exists to translate.

Secrets should come from the environment (`JANUS_BACKEND_API_KEY`), not from committed YAML.

## Extending coverage

1. Document the endpoint pair under `docs/api-comparison/endpoints/`.
2. Classify fields as Compatible, Rename, Convert, or Gap.
3. Add mapper functions and wire them in `mappers/registry.py`.
4. Expose the public path on the matching face router.

## Health

`GET /` and `GET /health` are Janus-native. The home page links to coverage, audit, and health. `/health` is intended for systemd and load-balancer checks.

## Compatibility audit

`GET /audit/start` and `GET /audit/report` are Janus-native. A session is bound either to the client IP (`?sessionID=myIP`, using `X-Forwarded-For` / `X-Real-IP` behind nginx) or to the public-face API key string itself. The same value is used to fetch the report (`/audit/report` from that IP, or `?sessionID=<key>`). Middleware records face traffic for active binds and labels each call ok / warn / fail / unknown against the endpoint catalog. Access logs include XFF and anonymized paths.
