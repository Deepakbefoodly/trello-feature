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
| Backend | 80 | Ordering (including a `hypothesis` property test), ownership across all 12 board-scoped endpoints, auth, validation |
| Frontend | 24 | The optimistic reordering functions, rollback on a rejected move, route guards |

The backend suite takes around 90 seconds, almost all of it bcrypt hashing at its
default work factor. That cost is deliberate — lowering it for tests would mean
shipping a configurable hashing cost, which is not a knob worth exposing.

Linting: `ruff check .` and `ruff format --check .` in `backend/`, `npx oxlint` in
`frontend/`.

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
