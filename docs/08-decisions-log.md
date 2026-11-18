# Decisions Log

Short records of choices, so a reader can see *why*, not just *what*. Format: context, decision, consequences.

## D-001: Fictional lender and synthetic data only
- **Context:** Loan data is highly sensitive; the project is a portfolio piece.
- **Decision:** LendFlow is fictional. Only synthetic data is used; the upload screen warns users.
- **Consequences:** No privacy risk from real people; demos are safe to publish. Legal compliance is shown as design, not as a license claim.

## D-002: AI is advisory, humans decide
- **Context:** Credit decisions affect people's finances and carry regulatory weight.
- **Decision:** The AI agent extracts, checks and summarises. It never approves or rejects.
- **Consequences:** Every application needs a human decision; AI outputs are stored with model and config for audit.

## D-003: E-signature deferred (Won't this release)
- **Context:** Appears as Must in one training document and Medium in another. Real e-signature needs a certified provider.
- **Decision:** Defer; document the legal basis in the compliance matrix.
- **Consequences:** The contract exists as a document entity; revisit later.

## D-004: Technology stack
- **Decision:** Next.js + TypeScript (frontend); FastAPI (Python) backend; PostgreSQL; Anthropic API for the agent; Docker, GitHub Actions; free-tier hosting.
- **Rationale:** Maximises hiring relevance (TypeScript, Python, SQL, CI/CD, AI), plays to existing frontend strength, and costs almost nothing.
- **Consequences:** Two languages to maintain; kept manageable by a monorepo and shared API contract (OpenAPI).

## D-005: Cost controls
- **Decision:** Mock mode for AI by default in tests and demos; cheapest model that passes the evals; monthly spend cap; per-request cost logging; free OCR first, model only where needed.
- **Consequences:** Near-zero running cost; the OCR-versus-model trade-off becomes a documented experiment.

## D-006: Prioritisation
- **Decision:** Must <= 60% of backlog (currently 50%).
- **Consequences:** Cut order if time runs short: LF-019, LF-020, LF-017, LF-014, LF-013.

## D-007: Illustrative business parameters
- **Decision:** Rates and thresholds are invented and configurable; marked as such throughout.
- **Consequences:** No claim about real market rates; stakeholder sign-off is shown as an open item.

## D-008: Authentication session design (LF-001)
- **Context:** LF-001 requires a 5-failure lockout for 15 minutes, a 30-minute idle logout, and short-lived tokens with refresh.
- **Decision:**
  - A locked account returns **423 "locked for 15 minutes"** so a genuine user knows to wait. This reveals that the email exists, but only after 5 failed attempts.
  - Wrong credentials return one generic 401 and take the same time whether or not the email is registered.
  - Each access JWT (15 minutes) is tied to a server-side session. Every authenticated request updates the session's last-activity time, so the idle timeout is exact.
  - Each refresh token works once and is replaced when used. Presenting the token that was just replaced revokes the whole session (theft signal) and is audited.
  - Failed logins for **unknown** emails are not audited, because doing so would mean storing the attempted email (personal data).
- **Consequences:**
  - One database write per authenticated request. That's acceptable at demo scale; throttle it if load grows.
  - Two browser tabs refreshing with the same token at the same moment will log the user out. Accepted as the safer side.
  - Only the immediately previous refresh token is checked for reuse; older tokens are simply rejected without revoking the session.

## Open items

| # | Question | Owner (simulated) | Needed by |
|---|---|---|---|
| Q1 | Acceptance rule for freelance and self-employed income | CCO + Risk | Before LF-007 build |
| Q2 | Handling of legacy 9-digit IDs | Compliance | Before LF-006 build |
| Q3 | Officer approval limit | CCO | Before LF-011 build |
| Q4 | Official consolidated text for C-04 and C-10 (effective dates, current circular) | Compliance | Before publishing the matrix |
| Q5 | Bank or consumer finance company model | Product Owner | Before release |
