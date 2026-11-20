# Deploying LendFlow (Fly.io)

Synthetic data only. See D-034 for the decisions behind this.

## Layout

| App | Config | Public | Notes |
|---|---|---|---|
| `lendflow-web` | `frontend/fly.toml` | yes (HTTPS) | Next.js; proxies `/api/*` to the API |
| `lendflow-api` | `backend/fly.toml` | no | FastAPI on `lendflow-api.internal:8000`; one machine; volume at `/data` |
| Postgres 16 | n/a | no | Fly Postgres or any provider; two database users (below) |

App names are global on Fly. If `lendflow-api` or `lendflow-web` is taken, rename them in both `fly.toml` files, `deploy.yml` and the `APP_BASE_URL` / `BACKEND_URL` values.

## Smoke test locally first

```
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
export DB_OWNER_PASSWORD=choose-one APP_DB_PASSWORD=choose-a-16-plus-char-one
docker compose -f docker-compose.prod.yml up --build -d --wait   # http://localhost:3100
docker compose -f docker-compose.prod.yml exec -e SEED_PASSWORD=... api python -m scripts.seed_users
docker compose -f docker-compose.prod.yml down -v
```

This runs the same images: migrate as the owner, provision the restricted role, run the API as that role.

## First-time setup

```
fly apps create lendflow-api && fly apps create lendflow-web
fly volumes create lendflow_data --app lendflow-api --region sin --size 1
# Create a Postgres 16 database named "lendflow" and note its owner connection string.
fly secrets set --app lendflow-api \
  JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  DATABASE_URL="postgresql+psycopg://lendflow_app:<APP_DB_PASSWORD>@<host>:5432/lendflow"
```

Note what is **not** set on the API app: the owner URL. It lives only in GitHub secrets and goes to the one-off migration machine.

GitHub repository secrets: `FLY_API_TOKEN` (`fly tokens create deploy`), `DB_OWNER_URL` (`postgresql+psycopg://<owner>:<pw>@<host>:5432/lendflow`), `APP_DB_PASSWORD` (the password used in `DATABASE_URL` above, 16+ characters).

## Deploy

Run the **Deploy** workflow (Actions > Deploy > Run workflow). It builds the API image, migrates and refreshes the restricted role, deploys the API (`--ha=false`: one machine), then deploys the web app.

First deploy only: create staff accounts.
```
fly ssh console --app lendflow-api -C "env SEED_PASSWORD=<choose> python -m scripts.seed_users"
```

## Scheduled jobs (LF-014, LF-017)

Run the API image on a schedule (Fly scheduled machines accept `hourly`, `daily`, `weekly`, `monthly`):
```
IMG=$(fly image show --app lendflow-api --json | jq -r '"registry.fly.io/\(.[0].Repository):\(.[0].Tag)"')
fly machine run "$IMG" --app lendflow-api --schedule hourly --restart no --entrypoint /bin/sh -- -c "python -m scripts.sla_sweep"
fly machine run "$IMG" --app lendflow-api --schedule daily  --restart no --entrypoint /bin/sh -- -c "python -m scripts.send_reminders"
```
These use the API's secrets (restricted database role), which is all they need. Re-create them after an image change, or they keep running the old image.

## Checks after deploying

- `https://lendflow-web.fly.dev/` loads and the calculator shows 4,896,311 VND/month for 100,000,000 / 24 months.
- Log in as the seeded supervisor; the audit log shows your real IP, not an internal `172.x`/`fdaa:` address.
- `fly logs --app lendflow-api` shows no errors; `GET /api/health` returns `{"status":"ok"}`.

## Known gaps

- The Fly config and `deploy.yml` are **untested**; the first run may need adjustment (in particular, confirm the one-off migration machine finishes before the API deploy starts, and run migrations by hand if not).
- Upload virus scanning, backups and a custom domain are not set up (D-034).
- One API machine only (uploads on a volume, in-memory rate limit).
