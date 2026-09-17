# Kanban

A Trello-style kanban board: boards hold lists, lists hold cards, and cards can be
dragged within and between lists. Every board belongs to exactly one user and is
invisible to everyone else.

- **Backend** — Python 3.11+, FastAPI, SQLAlchemy 2, PostgreSQL 16, Alembic.
- **Frontend** — React, TypeScript, Vite, TanStack Query, dnd-kit.

---

## Prerequisites

- Python 3.11 or newer (this was developed on 3.13)
- Node 20 or newer
- Docker, for the local PostgreSQL

---

## Setup

### 1. Start PostgreSQL

```bash
docker compose up -d --wait
```

This publishes PostgreSQL on **host port 5433**, not the usual 5432. A native
PostgreSQL service often already owns 5432, and the collision shows up as a
confusing authentication failure against the wrong server.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env
.venv/Scripts/python -m alembic upgrade head
```

On macOS or Linux use `.venv/bin/python` in place of `.venv/Scripts/python`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

---

## Environment variables

`backend/.env` — see `backend/.env.example`:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://kanban:kanban@localhost:5433/kanban` |
| `JWT_SECRET` | HS256 signing key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CORS_ORIGINS` | Comma-separated allowed origins for the browser client |
| `DB_SCHEMA` | Schema holding this app's tables. `public` locally; only needed when sharing an instance |

`frontend/.env` — see `frontend/.env.example`:

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Base URL of the API, default `http://127.0.0.1:8010` |

`.env` files are gitignored. Nothing in the repo contains a real secret.

---

## Running it

Two terminals.

```bash
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8010 --reload
```

```bash
cd frontend && npm run dev
```

Then open **http://localhost:5173**. Interactive API docs are at
http://127.0.0.1:8010/docs.

> **Why port 8010 and not 8000?** On the machine this was built on, Docker Desktop
> already listened on 8000 for both IPv4 and IPv6, while uvicorn bound only IPv4
> loopback. The browser resolved `localhost` to `::1`, reached Docker instead of the
> API, and every request failed with an empty response. 8010 avoids that. If you
> change it, update `VITE_API_URL` to match.

### Demo data

```bash
cd backend && .venv/Scripts/python seed.py
```

Creates **demo@example.com** / **demo-password** with a populated "Product" board.
Re-running it recreates that user and touches nothing else.

---

## Tests

Both suites are green. The backend suite needs PostgreSQL running — it creates and
drops its own `kanban_test` database per session and truncates every table between
tests, so it never touches development data.

```bash
cd backend && .venv/Scripts/python -m pytest
```

```bash
cd frontend && npm test
```

| Suite | Count | Covers |
|---|---|---|
| Backend | 99 | Ordering (including a `hypothesis` property test), ownership across all 12 board-scoped endpoints, auth, validation, database-URL rewriting, schema isolation |
| Frontend | 31 | The optimistic reordering functions, rollback on a rejected move, route guards, loading-indicator timing |

The backend suite takes around 90 seconds, almost all of it bcrypt hashing at its
default work factor. That cost is deliberate — lowering it for tests would mean
shipping a configurable hashing cost, which is not a knob worth exposing.

Linting: `ruff check .` and `ruff format --check .` in `backend/`, `npx oxlint` in
`frontend/`.

---

## Deploying

The API runs on **Render**, declared by `render.yaml` at the repo root, against an existing
PostgreSQL instance. The client runs on **Vercel**. Both deploy from `main`.

### 1. Render — the API

Dashboard → **New → Blueprint** → pick this repository. Render reads `render.yaml` and creates the
web service, generating `JWT_SECRET` itself.

`render.yaml` deliberately declares **no database** — this deployment reuses an existing PostgreSQL
instance (see *Sharing a database* below). One value must be set by hand:

- **`DATABASE_URL`** — marked `sync: false`, so Render prompts for it. Paste your existing
  database's **Internal** Database URL. It is not in the file because it carries credentials and
  the repo is public.

The build command installs the package and runs `alembic upgrade head`, so the schema is created on
the first deploy and kept current on every later one.

Copy the assigned API URL when it finishes, e.g. `https://kanban-api-xxxx.onrender.com`.

### Sharing a database with another application

Render's free tier allows one free PostgreSQL instance per account, so this app shares an existing
one rather than creating its own. Sharing an instance naively would be unsafe: the migration creates
`users`, `boards`, `lists`, `cards` and `alembic_version`, and `users` in particular is a name most
applications already use. Two apps sharing `public` would collide on it, and two Alembic histories
sharing one `alembic_version` row would each try to migrate away from the other's revision.

So every table this app owns lives in its **own schema**, set by `DB_SCHEMA` (default `public`,
`kanban` in `render.yaml`):

- `app/db.py` pins every connection's `search_path` to that schema, so unqualified table names can
  only ever resolve inside it.
- `alembic/env.py` creates the schema if absent — PostgreSQL accepts a `search_path` naming a schema
  that does not exist and silently resolves to nothing, so it cannot be assumed — and `alembic_version`
  is created unqualified, landing in the same schema. Each application keeps a separate history.
- The schema name is validated as a plain identifier in `Settings`, because it reaches DDL and a
  libpq connection option, neither of which accepts a bound parameter.

**Requirements when sharing:** the web service must be in the **same region** as the database, since
Render's internal network is per-region and the internal hostname will not resolve otherwise.

This was verified against a database whose `public` schema already contained all five conflicting
table names: the migrations created a parallel set under `kanban`, the app read and wrote only
there, and the existing rows in `public` were untouched. `backend/tests/test_schema_isolation.py`
covers the mechanism.

To go back to a dedicated database, drop `DB_SCHEMA` (it defaults to `public`) and add a
`databases:` block to `render.yaml` with `fromDatabase:` wiring `DATABASE_URL`.

### 2. Vercel — the client

Dashboard → **Add New → Project** → same repository, then:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Vite (auto-detected) |
| Build Command | `npm run build` (default) |
| Output Directory | `dist` (default) |
| Environment Variable | `VITE_API_URL` = the Render API URL from step 1 |

`VITE_API_URL` is read at **build** time, not runtime. Changing it later needs a redeploy, not just
an env var edit.

`frontend/vercel.json` adds an SPA rewrite so every path falls back to `index.html`. Without it, a
hard refresh on `/boards/<uuid>` asks Vercel for a file at that path and gets a 404 — and that is
exactly the URL you would paste to show someone a board.

### Production environment variables

Set by `render.yaml` unless noted:

| Variable | Source |
|---|---|
| `DATABASE_URL` | Set by hand in the dashboard (`sync: false`) - see step 1 |
| `JWT_SECRET` | Generated by Render on first deploy |
| `CORS_ORIGINS` | `*` — see below |
| `DB_SCHEMA` | `kanban` — see Sharing a database |
| `PYTHON_VERSION` | `3.13.7` |

Render supplies a `postgresql://` URL, which SQLAlchemy would resolve to psycopg2 — a driver this
project does not install. `Settings._force_psycopg_driver` in `backend/app/config.py` rewrites the
scheme to `postgresql+psycopg://`, so the platform's URL works untouched. That rewrite is covered by
`backend/tests/test_config.py`.

### Verifying a deploy

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://<your-api>.onrender.com/docs
```

Then register a throwaway account — a `201` proves the driver rewrite worked *and* that migrations
ran, which a healthy `/docs` alone does not:

```bash
curl -sS -X POST https://<your-api>.onrender.com/api/auth/register -H "Content-Type: application/json" -d '{"email":"deploy-check@example.com","password":"deploy-check-pw"}'
```

Finally, open the Vercel URL, create a board and a card, drag it to another list, and hard-refresh.
That exercises the ordering algorithm against Render's PostgreSQL rather than local Docker.

### Free-tier caveats

- **The API sleeps when idle.** A free Render web service spins down after a period of inactivity,
  and the next request blocks while it cold-starts — often tens of seconds. The loading bar (below)
  covers this, so the app reads as busy rather than broken, but it is still a long wait. If you are
  demoing it live, hit the API once beforehand.
- **The free database does not last forever.** Render removes free PostgreSQL instances after a
  limited period. Check the current policy on Render's pricing page before relying on a demo link.
- **Migrations run in the build command**, because Render's pre-deploy hook is a paid-instance
  feature. They therefore execute against the live database while the previous version is still
  serving. That is acceptable for one instance with additive migrations, and wrong at scale. On a
  paid instance, move that line from `buildCommand` to `preDeployCommand` in `render.yaml` — a
  failed migration then aborts the deploy and the old version keeps serving.

### A note on `CORS_ORIGINS=*`

The API accepts any origin. This is a deliberate choice for a demo with a separately-hosted
frontend and per-branch Vercel preview URLs, and it is less exposed than the blanket warning
suggests: authentication is a Bearer token in an `Authorization` header, not a cookie, so a browser
never attaches it automatically and a hostile page cannot ride a signed-in user's session — it would
need the token itself. `allow_credentials` is not enabled, which is also what makes the wildcard
valid at all; browsers reject `*` outright when credentials are on.

**This stops being acceptable** if authentication moves to cookies or `allow_credentials=True` is
added. Either change requires replacing the wildcard with an explicit origin list first. Tightening
it is a one-line environment variable change on Render and needs no code redeploy.

---

## Ordering: the design decision worth knowing

A card's place is a plain integer `position`, contiguous and 0-based within its
list. A list with *n* cards holds exactly `0 … n-1` — no gaps, no duplicates.

Moving a card shifts the block of siblings it jumped over by ±1 and then writes the
card's new position, all in one transaction that begins by taking a write lock on
the owning board row. Locking the board rather than the card is what makes
concurrent moves safe: it is the shifted *range* that needs protecting, not the one
row the user grabbed.

The `(list_id, position)` unique constraint is `DEFERRABLE INITIALLY DEFERRED`,
because a bulk shift passes through transiently duplicated positions before the
statement completes. Deferring the check to `COMMIT` keeps each shift a single
`UPDATE` instead of a carefully ordered row-by-row walk.

**The trade-off.** A move rewrites up to *n* rows, where a fractional rank
(LexoRank and similar) would rewrite exactly one. At board scale — tens of cards —
that write amplification is irrelevant, and plain integers stay readable and
debuggable when you are looking directly at the table. Obvious correctness was
chosen over write efficiency, deliberately. If lists ever grew into the thousands,
this is the decision to revisit.

All of this lives in `backend/app/ordering.py`, the only module permitted to write
`position`. `frontend/src/ordering.ts` mirrors it for optimistic updates, and both
test suites assert the same cases so the two cannot drift apart silently.

---

## Loading feedback

A thin bar across the top of the viewport shows whenever the app is waiting on the API
(`src/components/ProgressBar.tsx`). It reads TanStack Query's global counters, so it covers every
request without any call site knowing about it. Two rules make it useful rather than noisy:

- **It waits ~400ms before appearing.** Anything quicker shows nothing at all, because a bar that
  flashes on and off reads as a glitch rather than as progress.
- **It ignores card and list moves, and background revalidation.** A drag is applied optimistically,
  so by the time the request is sent the user has already seen it happen; announcing it as pending
  would contradict the screen. The same goes for the refetch every mutation triggers on settling —
  without excluding that, the bar reappeared a second after a drag had visibly finished.

It is deliberately non-blocking. A full-screen overlay would be impossible to miss during a
cold start, but it would also freeze the board on every drag, destroying the instant feel the whole
optimistic-move design exists to provide. Failures are reported separately by the rollback toast.

---

## Manual verification

1. Sign in as `demo@example.com` / `demo-password`.
2. Open the **Product** board. Drag a card within a list and to another list.
3. **Reload the page.** The order is unchanged.
4. Sign out, register a second account, and paste the first user's board URL.
   It reports that the board does not exist — a 404, never a 403, so the URL
   cannot be used to discover that someone else's board is real.

---

## What is not here

Deliberately out of scope: board sharing and members, labels, due dates,
checklists, comments, real-time collaboration, refresh tokens, password reset,
archiving, search, and pagination.

Known limitations:

- The access token is kept in `localStorage`, which an XSS bug could read. An
  httpOnly cookie would be safer but needs CSRF handling; the trade-off was made
  knowingly for a single-page app with no cookie flows.
- Passwords are capped at 72 **bytes**, which is bcrypt's hard limit — it raises
  rather than truncating. The cap is enforced on byte length, not character count,
  because a multibyte password can be well under 72 characters and still exceed it.
- Other sessions' changes appear on refetch, not live.
