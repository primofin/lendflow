# CLAUDE.md: LendFlow

Guidance for Claude Code working in this repository.

## Project

LendFlow is a **fictional** digital lending app (portfolio project). Borrowers apply online; an AI agent extracts and summarises documents; loan officers and supervisors decide. All data is **synthetic**. Read `docs/00-project-brief.md` first, then `docs/04-user-stories-backlog.md`.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Pydantic v2, pytest, ruff
- **Frontend:** Next.js (App Router), TypeScript (strict), Tailwind, Vitest, Playwright
- **AI:** Anthropic Python SDK; model name from environment, never hard-coded
- **Ops:** Docker Compose for local; GitHub Actions for CI

## Layout

```
backend/app/{api,core,models,schemas,services,agents}
backend/tests/
frontend/src/{app,components,lib}
evals/               # AI evaluation set and runner
docs/                # BA documents (source of truth for requirements)
```

## Commands (create these as the project is built, then keep this list accurate)

```
# database (Postgres 16 on host port 5433; creates lendflow + lendflow_test)
docker compose up -d --wait

# backend (first time: cp .env.example backend/.env and set JWT_SECRET)
cd backend && uv sync
cd backend && uv run pytest              # tests (uses lendflow_test, migrates it)
cd backend && uv run python -m scripts.seed_users   # synthetic officer + supervisor
cd backend && uv run ruff check .        # lint
cd backend && uv run alembic upgrade head
# audit_logs and decisions are append-only (triggers), so dev rows cannot be deleted; to reset the dev database:
#   docker compose down -v && docker compose up -d --wait && (cd backend && uv run alembic upgrade head)
cd backend && uv run fastapi dev app/main.py

# frontend
cd frontend && npm run dev
cd frontend && npm test
cd frontend && npm run lint

# AI evals
cd evals && uv run python run_evals.py --mode mock
```

## Working rules

1. **Plan first.** For any non-trivial change, propose a short plan and wait for approval before editing.
2. **One story at a time.** Implement a single `LF-xxx` story per branch. Do not start the next until tests pass.
3. **Traceability.** Reference the story ID in code comments, test names and commit messages (`feat(LF-012): ...`, `test_lf012_...`).
4. **Tests with code.** Every endpoint and rule gets tests, including negative cases taken from the acceptance criteria.
5. **Small commits.** Commit after each green step. Never commit secrets, `.env`, or real personal data.
6. **Explain diffs.** Summarise what changed and why; flag anything you are unsure about.

## Domain rules (do not break)

- The AI **recommends**; a human **decides**. No code path may approve or reject automatically (BR-15).
- Decisions and audit-log rows are **append-only** (BR-14, LF-016).
- Rejections require a reason code and a plain-language explanation (BR-13).
- Money is stored as integer VND or `numeric`, never float.
- Calculator rule: annuity, reducing balance; test against `docs/02-business-rules.md` worked example (100,000,000 VND, 24 months, 16% → 4,896,311 VND per month).
- No processing of personal data without recorded consent (BR-21).

## AI and cost rules

- `AI_MODE` is `mock` by default. `live` requires an API key and enforces `AI_MONTHLY_BUDGET_USD`.
- Log model, config version, input references, cost and timestamp for every AI call (BR-16, BR-19).
- Prefer the cheapest model that passes `evals/`. Use prompt caching and short outputs.
- Never send real personal data; use files in `evals/data/` (synthetic).

## Security

- Hash passwords (argon2 or bcrypt); short-lived JWTs; enforce authorization in the API, not only the UI.
- Validate upload type and size (JPG, PNG, PDF, <= 5 MB). Store files outside the web root.
- Do not log personal data or secrets.

## Style

- Python: type hints everywhere, ruff-clean, small functions, services separate from routes.
- TypeScript: strict mode, no `any`; API types generated from the OpenAPI schema.
- Error messages are specific and actionable.

## Legal and docs

- Treat `docs/05-compliance-matrix.md` as a living document; do not invent article numbers. Mark unverified items "R" or "V".
- Business parameters in `docs/02-business-rules.md` are illustrative and configurable; do not hard-code them.
