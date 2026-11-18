#!/usr/bin/env bash
# Regenerate API types from the backend's OpenAPI schema (CLAUDE.md: types are generated).
# Needs uv on PATH. Commit openapi.json and src/lib/api/schema.d.ts together.
set -euo pipefail
cd "$(dirname "$0")/.."
(cd ../backend && JWT_SECRET="${JWT_SECRET:-schema-export-only-not-a-real-secret-0000}" \
  uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))") > openapi.json
npx openapi-typescript openapi.json -o src/lib/api/schema.d.ts
