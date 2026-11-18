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

## D-009: Application submission and consent (LF-004)
- **Context:** BR-21 forbids processing personal data before explicit consent; LF-004 requires consent to be recorded with a version and timestamp.
- **Decision:**
  - Submission is one atomic request containing the loan, the profile and the consent. There are no server-side drafts yet, so no personal data is stored before consent. Every rule is checked before anything is saved.
  - The consent text is versioned in code. A submission with a missing or out-of-date version is refused, and a consent record is created once per user and version.
  - Legacy 9-digit national IDs are **rejected** with "National ID must be 12 digits" until Compliance resolves open item Q2.
  - `annual_rate` stays empty on the application until the calculator (LF-003) supplies it.
  - Validation error responses report only the field and the reason, never the submitted values, so personal data is not echoed back.
- **Consequences:** The frontend must keep form state until the user submits. Server-side drafts, officer-created applications and consent withdrawal (LF-018) are later stories.
  - Age is calculated on the server's UTC date, so near midnight in Vietnam it can be off by a day.
  - A second application overwrites the borrower's saved profile with the newly submitted details; there is no history of earlier values.
  - Consent is recorded once per user and consent version, not per application, because the data model has no link between them.
  - The "maximum age 65 at maturity" rule cannot trigger with the documented ranges (60 plus a 60-month term is exactly 65). It is kept as a setting and tested by lowering the limit.

## D-010: Loan calculator rounding and rates (LF-003)
- **Context:** The worked example in `docs/02` gives a monthly payment of 4,896,311 VND and a total repaid of 117,511,465 VND. Multiplying the rounded payment by 24 gives 117,511,464, so the documented total was rounded from the exact figures.
- **Decision:**
  - The monthly payment and the total repaid are each rounded once (half up) from the exact figures. Total interest is the total minus the principal. This reproduces the documented example, and the code states the rule.
  - All money uses `Decimal` and whole VND, never float.
  - Rates are the illustrative tiers of BR-05 (up to 12 months 14%, 13 to 36 months 16%, over 36 months 18%), held in settings. A 0% rate falls back to amount divided by term.
  - A submitted application stores the rate quoted for its term in `annual_rate`.
- **Consequences:** The borrower's real instalments would sum to 1 VND less than the quoted total in the worked example, and by up to a few VND for other loans. A repayment schedule, in a later story, will decide how the last instalment is adjusted. The calculator and the application share one set of amount and term validators, so they cannot disagree.
  - The calculator is public and has no rate limiting. The calculation is cheap, but add limiting before any deployment.
  - `annual_rate_percent` in the response is a float for display only; every calculation and the stored rate use `Decimal`.
  - A term above the highest configured tier (60 months) returns an error. That cannot happen while terms are limited to the allowed list.

## D-011: Document upload (LF-005)
- **Context:** Borrowers upload identity and income documents. These are sensitive, and the demo allows synthetic files only (BR-24).
- **Decision:**
  - The file type is decided from the file's first bytes (JPEG, PNG, PDF). The filename and the Content-Type header are never trusted. Limit: 5 MB.
  - Files are stored under a random name in a folder outside any web root, with owner-only permissions. **The original filename is not stored**, because names such as `CCCD_<name>.jpg` are personal data.
  - A retried upload is recognised by its content: the same application, document type and bytes can exist only once, enforced by the database. A retry returns the existing document with 200.
  - Downloads go through the API with the access check and are served as attachments with `nosniff`. Staff list and download actions are audited.
  - A coarse request-size guard rejects oversized uploads before they are buffered, because FastAPI parses a multipart body before it runs authentication.
  - `delete_after` stays empty until a final decision exists (LF-011); the retention job (BR-23) is a later story.
- **Consequences:**
  - There is no virus scan and no inspection inside PDFs; the attachment and `nosniff` headers are the protection for now. Add scanning before any real deployment.
  - A deliberate re-upload of an identical file under the same type counts as a duplicate.
  - A file between 5 MB and about 5.06 MB gets the friendly "larger than the limit" message; anything bigger gets the shorter request-level message.
  - Deleting or replacing a document is not offered; the permission matrix gives borrowers no delete right.

## D-012: Audit log is append-only and searchable (LF-016)
- **Context:** BR-14 and LF-016 require that audit entries cannot be edited or deleted through the application, and that a supervisor can reconstruct an application's history. The app connects to Postgres as a superuser in development, so revoking privileges would not stop it.
- **Decision:**
  - Database triggers reject `UPDATE`, `DELETE` and `TRUNCATE` on `audit_logs` for every connection. An ORM guard fails fast with a clear error, and the only audit route is `GET`.
  - Each entry gets a database-assigned `seq` that orders and pages the log exactly, because many entries can share a timestamp.
  - Each entry that concerns an application, or one of its documents, carries `application_id`, so the full history is one indexed query. The migration backfills existing rows before the triggers are installed.
  - Supervisors read all entries. Officers read only their own actions, enforced inside the query so filters cannot widen it. Borrowers are refused, and the refusal is audited.
  - `limit` is capped at 200 and larger values are rejected rather than silently clamped, so a client paging with `offset += limit` cannot skip entries. Reading the audit log is not itself audited, because entries hold ids, actions and IP addresses, never borrower data.
- **Consequences:**
  - Dev rows cannot be deleted. Reset the dev database with `docker compose down -v` (see CLAUDE.md).
  - `seq` follows insertion, not commit order, so two transactions that commit at nearly the same moment may appear in either order.
  - The trigger stops the application but not someone who owns the table or is a superuser, since they can drop it.
- **Before any real deployment:** run the app as a database role that can only `INSERT` and `SELECT` on `audit_logs`, separate from the role that owns the tables and runs migrations.
- **Open for LF-018:** audit entries hold actor ids and IP addresses, which are personal data, and they can no longer be changed. Decide how data-subject deletion requests treat them (for example, anonymising the user record while the entries keep a non-identifying actor id).

## D-013: Required documents by income type (LF-007)
- **Context:** BR-06 ties the required documents to the income type, and several requirements are alternatives ("payslips or bank statements"). The rules must be changeable without code, and the freelance and self-employed acceptance rule is still open (Q1).
- **Decision:**
  - Rules are data: `income_type_rules`, `required_document_rules` and `required_document_options`, seeded by migration from `docs/02` section 3. A requirement is met by **any one** of its options, which the single `doc_type` column in the first draft of the data model could not express.
  - The checklist is a pure function of the rules, the documents on file and the requirements waived. A document beats a waiver. Only mandatory requirements decide the status: `complete`, `exception` (everything satisfied or waived, at least one waived) or `incomplete`.
  - An officer can declare a **mandatory, still-missing** requirement unavailable. The request carries only the requirement, with no free text, so no personal data can slip in. The file is flagged as an exception and assigned to the active supervisor with the fewest open exception files (oldest account on ties). With no active supervisor the exception is still recorded, unassigned.
  - The existing officer-limit check (BR-10) already refuses an officer on an exception file, so only a supervisor can decide it.
  - Income type "Other" always goes to a supervisor, so it is flagged and assigned at submission.
  - Each application stores a **snapshot of its income type**. The borrower profile is overwritten by later applications, and an earlier application's requirements must not change.
  - The rules are read-only through the API for now (officers and supervisors). Borrowers can read the checklist of their own application, which is derived from their own uploads, but not the rules panel.
- **Consequences:**
  - The checklist checks the document **type** only. Whether "3 months of payslips" really covers three months is for a human or the AI review (LF-009).
  - A requirement declared unavailable stays flagged even if the document is uploaded later. The checklist shows it satisfied, and the exception remains for a supervisor to decide.
  - Supervisor editing of rules is a later story. Changing rules while files are in flight needs its own design for audit and for what happens to those files.
  - Assignment is by simple load. LF-010 (queues) and LF-017 (escalation) can replace it.

## D-014: Role-based access control (LF-002), recorded retrospectively
- **Context:** LF-002 requires that each role can do only what `docs/01` allows, enforced in the API and not just hidden in the UI. This record was written after the story was merged; it covers choices that were previously only in review notes.
- **Decision:**
  - Roles are enforced by a `require_roles` dependency on each route plus ownership checks in the services. Every refusal returns 403 and is audited (`access.denied`, `application.access_denied`). An unknown role is denied by default.
  - Borrowers read only applications of their own profile. Officers and supervisors read all applications **for now**, because nothing can be assigned until LF-010, which narrows officers to assigned or queued files as the matrix says. Staff reads are audited (RBAC rule 4).
  - A request for an application that does not exist returns 404, while one that belongs to someone else returns 403. This reveals that the id exists, which is acceptable because ids are random UUIDs and cannot be guessed.
  - User management is supervisor-only. A supervisor cannot change their own role, so the system cannot lose its last supervisor by accident. One supervisor can still demote another.
  - Self-registration always creates a borrower. Staff accounts are created by a supervisor or the seed script.
  - The officer limit (BR-10) is a pure function, `check_decision_authority`: officers are refused at or above 200,000,000 VND, or when the exception flag is set, with "Supervisor approval required". The limit is a setting. It is tested but not connected to an endpoint until the decision story (LF-011).
  - Minimal `borrower_profiles` and `applications` tables were created here so ownership could be enforced; LF-004 extended them.
- **Consequences:**
  - Officers can see every application until LF-010.
  - An officer approving an application they created on a borrower's behalf above the limit (RBAC rule 2) is not handled until LF-011.
  - Re-authentication for sensitive actions is a stretch goal and is not built.

## D-015: How the code is tested and trusted
- **Context:** The domain rules (consent, authorization, money, audit) are expensive to get wrong, and a green test suite only helps if the tests can actually fail.
- **Decision:**
  - Tests run against a real Postgres database (`lendflow_test`), not SQLite, so constraints, triggers, `numeric` and the migrations behave as they will in production. Each test runs in a transaction that is rolled back. Time-dependent rules use an injectable fake clock.
  - Tests for a story are written first and run to confirm they fail for the right reason.
  - For rules where a silent mistake is costly (access control, consent, money, uploads, audit), the rule is deliberately broken once to check that at least one test fails, then restored. A mutation that no test notices means a missing test, unless another layer makes the behaviour identical (for example a database constraint backing an application check).
  - One story per branch, merged to `main` with a merge commit after the tests pass. Choices made while building are recorded here in the same branch.
- **Consequences:** The suite is slower than an in-memory one (about 25 seconds). Contributors need Docker for Postgres.

## D-016: Officer queue (LF-010)
- **Context:** The state machine puts files in `IN_REVIEW` once "checks done", but the checks (LF-006, LF-008) do not exist yet. The story also filters on high DTI and fast-track, which need CIC and verified-income data that is not built.
- **Decision:**
  - `IN_REVIEW` is added. A file moves from `SUBMITTED` to `IN_REVIEW` as soon as no mandatory document is missing, checked after each upload and after each officer waiver. The move writes a status-history row and an `application.queued` audit entry. LF-008 will add its own condition to this step.
  - `high_dti` and `fast_track` are stored booleans, false until LF-008 and LF-009 compute them (BR-07, BR-09). The queue filters on them now so the API contract does not change later; tests set them directly.
  - `GET /queue` is for officers and supervisors. Supervisors see every file. Officers see unassigned files and their own, so one officer does not pick up a colleague's file. Default is `IN_REVIEW` only, oldest first; `status=SUBMITTED` shows files still waiting for documents.
  - Paged with `limit` (max 200, larger values rejected) and `offset`, with a total count; an index on `(status, submitted_at)` keeps the first page fast. An empty result carries the message "No applications waiting".
  - Each queue read is audited (`queue.view`). Rows show the applicant's name, amount, term, flags and age, and no documents or identity numbers.
  - Uploads stay open on `IN_REVIEW` so a borrower can still add optional documents.
- **Consequences:**
  - Officers are narrowed in the queue list only. `GET /applications/{id}` still lets any officer read any file, as D-014 noted; narrowing it needs a decision on what happens to exception files assigned to a supervisor, and is left for LF-011.
  - The supervisor-assignment rule in D-013 now counts `IN_REVIEW` files as open.
  - Nothing assigns `assigned_officer` yet, so every file appears unassigned to officers until LF-011 or a later story assigns it.
  - No frontend exists, so the queue screen is not built; this story is API only.

## D-017: Decisions with reason codes (LF-011)
- **Context:** BR-12 to BR-15 need four outcomes, a mandatory explanation for rejections, immutable decisions and no automatic outcome. D-014 and D-016 left officer file access and the authority check for this story.
- **Decision:**
  - `decisions` is append-only, like the audit log: database triggers reject UPDATE, DELETE and TRUNCATE, the ORM refuses them, and no route edits a row. A database `seq` defines "latest", so ordering never depends on clocks.
  - Reason codes are data (`reason_codes`), seeded with **illustrative** codes. The real list is open item Q6.
  - A **rejection** needs a reason code, an explanation of at least 20 characters, and the documents or conditions that could change the result (BR-13). A **request for information** needs an explanation. Approve and refer take no reason code or conditions. Explanations are limited to 1,000 characters.
  - Transitions follow docs/03: approve, reject and request info from `IN_REVIEW` or `REFERRED`; refer only from `IN_REVIEW`. Anything else is a 409 that names the status.
  - Authority: an officer approving at or above the limit or on an exception file gets "Supervisor approval required" (BR-10). An officer may still reject such a file or refer it. A referred file can be decided only by a supervisor. Only officers refer; a supervisor decides directly. Referring assigns the supervisor with the fewest open files if none is assigned.
  - **Corrections:** only a supervisor, only for the latest decision, and only approve or reject, by sending `supersedes_id`. The new entry links to the old one, which stays visible in `GET /applications/{id}/decisions`.
  - **Borrower view:** the latest outcome, and for a rejection or request the explanation and conditions. A referral is internal and not shown; who decided is never shown; the internal note on an approval is not shown.
  - Decision audit entries hold ids and actions only, never the explanation text.
  - **Officer scoping now applies to files too:** an officer may open or decide a file only if it is unassigned or theirs (403 and an `application.access_denied` entry otherwise). `POST /applications/{id}/claim` takes an `IN_REVIEW` file; deciding also claims it. Supervisors see all. This closes the gap noted in D-014 and D-016.
  - BR-15: `APPROVED` and `REJECTED` are set only inside the decision service, as the result of a decision row.
- **Consequences:**
  - A file in `NEEDS_INFO` has no way back to the queue until LF-012 adds borrower resubmission; borrowers cannot upload to it yet.
  - The self-created-on-behalf rule (RBAC rule 2) is not enforced because staff cannot create applications on a borrower's behalf yet.
  - A correction does not notify the borrower; notification is LF-012.
  - Fast-track approval is tested with the flag set directly, since LF-008 and LF-009 compute it.
  - Dev decision rows cannot be deleted; the database-reset note in CLAUDE.md covers this.

## D-018: Borrower status tracker and mock email (LF-012)
- **Context:** The borrower needs to see where the file is, what to do when information is requested, and be told when the status changes. LF-011 left `NEEDS_INFO` as a dead end, and the project has no mail provider and may not send real personal data.
- **Decision:**
  - `GET /applications/{id}/tracker` returns the four steps from docs/03 (Received, Under assessment, Awaiting approval, Completed) with a state (`done`, `current`, `upcoming`, `skipped`) and the time of the last update, taken from the status history. A step that was never entered, such as Awaiting approval on a direct approval, is `skipped` with no time. A referral shows as "Awaiting approval"; the word "referred" and the supervisor are never shown.
  - In `NEEDS_INFO` the tracker adds the officer's request in their words, the mandatory documents still missing (label and accepted types), the existing upload URL, and whether the file can be resubmitted.
  - Borrowers can upload in `NEEDS_INFO`. `POST /applications/{id}/resubmit` (owner only) is allowed only from `NEEDS_INFO` and only when no mandatory document is missing, and returns the file to `IN_REVIEW` with the same officer. It does not require a new upload, because the borrower has no other way to answer a request that is not about a document.
  - **Email is a mock.** A message is a row in `outbox`, written in the same transaction as the status change, so a refused or rolled-back change sends nothing. It names the recipient by user id, holds a status line and a link, and never contains amounts, names, identity numbers or decision text. A real sender is a later, separate change. Emails go out when the file is queued, when information is requested, on resubmission, and on approval or rejection (including corrections). A referral sends nothing.
  - Each queued message is audited (`notification.queued`) with the outbox id and no text.
- **Consequences:**
  - "I receive an email" is verified only as a row in the outbox, not delivery to a mailbox.
  - Borrowers cannot yet read their own notifications through the API.
  - Status history has no sequence number, so two changes with the same timestamp have no defined order. Real requests differ by microseconds; tests advance the clock. If this ever matters, add a database sequence as for `decisions`.
  - Withdrawal, reminders and SLA emails belong to LF-014 and LF-017.
  - Still API only; there is no frontend, so the progress bar and upload button are not drawn.

## D-019: LF-009 AI review summary moved from Must to Should
- **Context:** All other Must stories were built. LF-009 was Must because the AI review is the project's core AI feature. The product owner judged that the lending flow does not depend on it.
- **Decision:** LF-009 is **Should**. The lending flow (apply, queue, decide, track, audit) works without it, and its own acceptance criteria require files to stay reviewable by hand when the AI is unavailable. The release plan builds the frontend first and returns to LF-009 afterwards.
- **Consequences:**
  - Must is now 9 of 20 (45%), under the 60% ceiling.
  - Without LF-009 the release has no AI feature, which is the headline of the brief's AI scope. If time runs short, LF-009 is the first Should to protect, not to cut.
  - The `high_dti` flag stays false until LF-008 or LF-009 computes it.
  - The LF-009 plan (on-demand review, DTI as a rule, text eval fixtures, provider interface, cost cap) is unchanged and was approved in principle but not started.

## D-020: Frontend foundation (F0)
- **Context:** All Must stories exist as an API only. `frontend/` held only a `.gitkeep`. CLAUDE.md asks for Next.js (App Router), strict TypeScript, Tailwind, Vitest and Playwright, API types generated from OpenAPI, and short-lived JWTs.
- **Decision:**
  - The browser talks only to the Next.js app. `/api/*` is forwarded to FastAPI by a rewrite, so the backend needs **no CORS**. Four route handlers under `/api/auth` (login, register, refresh, logout) call the backend and move the **refresh token into an httpOnly, SameSite=Strict cookie** scoped to `/api/auth` (Secure in production). The page only ever receives the short-lived access token, which it keeps in memory. A page reload gets a new access token from the cookie.
  - The API client sends the bearer token, refreshes once on a 401 and retries, shares one refresh between parallel requests (refresh tokens rotate with reuse detection, so two at once would log the user out), and turns the backend's `detail` (a string, or a list of field issues) into one readable message.
  - API types are generated by `npm run gen:api` from the backend's OpenAPI schema into `src/lib/api/schema.d.ts`; `openapi.json` is committed so the frontend builds without the backend.
  - Tailwind with plain components, no UI kit. The scaffold's `cacheComponents` and React compiler settings are kept.
  - Every page carries a demo banner: synthetic data only.
  - The screens come in slices, one branch each: login and register, calculator and application, documents and tracker, officer queue and decisions, audit log.
- **Consequences:**
  - The backend sees the Next.js server's address as the client IP, so audit entries and login lockouts made through the app record that address, not the user's. Forwarding the real IP needs a trusted-proxy setting on the backend and is not done yet.
  - The `Secure` cookie flag is set in production builds. Browsers other than Chrome may refuse it over plain `http://localhost`, so use `npm run dev` for local work.
  - `npm audit` reports 18 vulnerabilities, all in dev tooling (Vitest, ESLint and their dependencies); the production dependencies report none. The suggested fix downgrades Vitest, so it was not applied. Revisit when upstream releases fix them.
  - No GitHub Actions workflow exists for the backend or the frontend yet, although CLAUDE.md lists CI. That needs its own change.
  - Playwright is installed but has no tests until the first screens exist, and its browsers are not downloaded yet.

## D-021: Login, register and role-aware navigation (F1; LF-001, LF-002)
- **Context:** The first screens. They must show the API's exact messages, hide what a role may not use, and never keep secrets where page scripts or another page can reach them.
- **Decision:**
  - `/login` and `/register` share one form. Errors appear as the API wrote them (duplicate email, wrong credentials, the lockout text, the password-policy message). A labelled field, a password hint tied to the field with `aria-describedby`, and a disabled button while sending.
  - The header shows Log in and Register to visitors, and the user's email and role with Log out otherwise. The **Users** link is shown only to supervisors, and `RequireRole` shows "You do not have access to this page" to others and sends visitors to log in. This is a courtesy; the API still refuses the call.
  - `/admin/users` (supervisor): list users, create a user with a role, change a role. A refused change (for example a supervisor changing their own role) shows the message and the list is reloaded, so the select shows what the server holds.
  - **Idle sign-out:** the server enforces the 30-minute timeout. When a signed-in user's session can no longer be renewed, the client signs them out and the login page says "You were signed out after being idle." There is no client timer.
  - Next.js keeps a page it left alive but hidden, so the login form (and its state) stays in memory after login. The password field is therefore emptied on success.
  - Browser tests (Playwright, Chromium) run the real backend on port 8100 against `lendflow_test`. `backend/scripts/e2e_reset.py` wipes and re-seeds it and refuses any database whose name does not end in `_test`. The suite shares one database, so it runs one worker.
- **Consequences:**
  - The five-failed-logins lock is tested end to end, but not the 15-minute unlock (backend tests cover it) and not the real 30-minute idle timeout (simulated by a 401 plus a cleared cookie).
  - Running `npm run test:e2e` wipes `lendflow_test`, which `pytest` also resets, so the two cannot run at the same time.
  - Playwright needs a Chromium download (about 100 MB) and `uv` on the PATH.
  - Borrower and staff home pages show a "coming next" note until the application, tracker and queue screens exist.

## D-022: Calculator and application screens (F2; LF-003, LF-004)
- **Context:** The terms, amount range and purpose threshold are configurable backend settings, but the API did not expose them, so a browser form would have had to copy them.
- **Decision:**
  - New public `GET /loan-terms` returns the allowed terms, amount range and the amount from which a purpose is required. Both forms read it, so the screens follow the configuration.
  - `/calculator` (public) recalculates as the user types (300 ms debounce, stale requests cancelled) and has a Calculate button for keyboard and screen-reader users. Non-numeric or out-of-range amounts show a message under the field and call nothing. The result states the method and the rate. "Apply with these terms" passes only amount and term in the URL.
  - `/apply` (borrower) has loan, about-you and consent sections. All state stays in the form until the single submit request (D-009). Personal data is never put in the URL or browser storage and is cleared after a successful submit (Next keeps the page alive, hidden).
  - Unticked consent blocks submission, highlights the checkbox and moves focus to it. The consent text lists every purpose and the retention period. If the server says the consent text changed, the form reloads it and unticks the box.
  - Client checks (amount range, purpose threshold, 12-digit ID, required fields) only save a round trip. Server field errors are mapped under their inputs; other server messages (age rules) show as a form message with the data kept. Age rules are not copied into the browser.
  - `/applications/[id]` is a minimal confirmation (status, amount, term, purpose). F3 grows it into the tracker.
- **Consequences:**
  - A second application overwrites the stored profile (D-009).
  - Borrowers have no list of their applications yet; they reach one only after submitting.
  - A server-side age failure is shown as a general message because the API returns it without a field name.

## D-023: Borrower application page: tracker, checklist, uploads (F3; LF-005, LF-007, LF-012)
- **Context:** After submitting, a borrower needs one place to see progress, what is still required, and to add documents, and a way back to it later.
- **Decision:**
  - `/applications/[id]` is the borrower's single page: summary, progress (Received, Under assessment, Awaiting approval, Completed, each with its last update), a needs-info panel, the required-documents checklist, and the document list with the synthetic-data notice.
  - A request for information shows the officer's words and the exact missing items, each with an upload control. "Resubmit for review" appears only when the API says `can_resubmit`. The decision box is shown for approvals and rejections only; a request is shown in the needs-info panel, so the message is not duplicated.
  - The checklist is the borrower view of LF-007: each item is uploaded, not needed or not uploaded yet, with "Complete" in green. The officer's panel and the "No invoices available" exception stay with the officer screens (F4).
  - Uploads check type and size in the browser for a specific message; the server still checks the real file content. Re-sending the same file is recognised ("already uploaded") and adds no row. A failed upload says a retry creates no duplicate.
  - Upload controls are hidden once the status no longer accepts documents (mirrors `UPLOADABLE_STATUSES`; the API still refuses).
  - New `GET /applications` (borrower only, newest first by submission time) feeds "Your applications" on the home page, so a borrower can return to the tracker after logging in again.
  - Borrowers get no download or preview link; staff downloads are audited and belong to F4.
- **Consequences:**
  - The client keeps its own copy of the uploadable statuses; if the backend list changes, the screen shows controls the server then refuses (with the server's message).
  - A missing-items list in the needs-info panel covers mandatory items only, as the API computes it.
  - Email notifications have no screen; they are backend-only (outbox).

## D-024: Officer queue, file view and claim (F4a; LF-010, LF-011, LF-007 officer side)
- **Context:** Staff had no API that returned the applicant's details, so a file view could not show the income, date of birth or address a decision depends on.
- **Decision:**
  - New staff-only `GET /applications/{id}/review` returns the loan, the applicant's profile, flags and whether the file is held. It uses the same access rules and read audit as the application endpoint: an officer cannot open a colleague's file (403, audited) and a borrower gets 403.
  - The **national ID is masked** to its last four digits. Staff confirm identity from the documents; the full number is not needed on screen.
  - Who holds the file is shown as "You", "Another officer" or "Nobody yet" (and whether a supervisor is assigned), not a name.
  - `/queue` (officer, supervisor): status and flag filters, oldest or newest first, paging by 50, "No applications waiting" when empty, a Refresh button. There is no live refresh.
  - `/review/[id]` (staff): loan, applicant, flags, claim (officers, unassigned IN_REVIEW files), the checklist with "No <document> available" (officers, missing mandatory items), and documents. Supervisors see the file but cannot claim or declare exceptions.
  - A document opens through an authorised request, not a link, because the file endpoint needs the login header. The new tab is opened inside the click (so a pop-up blocker allows it) and pointed at the file once the request returns; on failure the tab is closed and the server's message is shown.
  - The requirements panel endpoint is not used: the checklist already lists mandatory and optional items for the applicant's income type.
- **Consequences:**
  - Decisions, the decision history and corrections are F4b.
  - Queue rows and the file view show personal data to staff; every read is audited.
  - Browser tests wait for the checklist to render before counting items. Two tests had counted too early and failed intermittently; they now pass on repeated runs.

## Open items

| # | Question | Owner (simulated) | Needed by | Status |
|---|---|---|---|---|
| Q1 | Acceptance rule for freelance and self-employed income | CCO + Risk | Before release | Interim: illustrative rules seeded, changeable as data (D-013) |
| Q2 | Handling of legacy 9-digit IDs | Compliance | Before LF-006 build | Interim: rejected with "National ID must be 12 digits" (D-009) |
| Q3 | Officer approval limit | CCO | Before LF-011 build | Interim: 200,000,000 VND from BR-10, configurable (D-014) |
| Q4 | Official consolidated text for C-04 and C-10 (effective dates, current circular) | Compliance | Before publishing the matrix | Open |
| Q5 | Bank or consumer finance company model | Product Owner | Before release | Open |
| Q6 | Official list of rejection reason codes | Compliance + Risk | Before release | Interim: illustrative codes seeded as data (D-017) |
