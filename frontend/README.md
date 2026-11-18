# LendFlow frontend

Next.js (App Router), TypeScript strict, Tailwind. Demo only; all data is synthetic.

```
cp .env.example .env.local     # BACKEND_URL, where /api requests are forwarded
npm install
npm run dev                    # http://localhost:3000 (start the backend first, see ../CLAUDE.md)
npm test                       # Vitest
npm run lint && npm run typecheck
npm run gen:api                # regenerate src/lib/api/schema.d.ts from the backend OpenAPI schema
```

- The browser only talks to this app. `next.config.ts` forwards `/api/*` to FastAPI, and the
  route handlers in `src/app/api/auth/` keep the refresh token in an httpOnly cookie. The access
  token lives in memory (`src/lib/api/client.ts`).
- API types are generated, not hand-written. Commit `openapi.json` and `schema.d.ts` together.
- This Next.js version differs from older ones. `AGENTS.md` (written by the scaffold) points to the
  matching docs in `node_modules/next/dist/docs/`.
