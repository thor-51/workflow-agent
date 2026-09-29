# Workflow Automation Agent

An Issue-to-Resolution workflow automation system built with FastAPI, LangChain, and LangGraph.
A user submits a software issue; the system classifies it, searches a local knowledge base,
proposes a remediation plan, pauses for human approval when the action is risky, executes
allowlisted tools, validates the result, and persists the full execution history.

> **Status: under construction (Phase 2 of 10 complete).** Sections marked _TODO_ are filled in
> as the corresponding phase is implemented. Nothing here describes a feature that is not
> implemented and tested.

## Problem statement
_TODO (Phase 10)_

## Architecture
_TODO (Phase 10) — see the design in the project plan: API → services → LangGraph → tools/repositories → database._

## Workflow diagram
_TODO (Phase 4/10)_

## Tech stack
Implemented so far: Python 3.11+, FastAPI, Pydantic v2 / pydantic-settings, structlog, SQLAlchemy 2.x, Alembic, SQLite, pytest, ruff, mypy.
Planned: LangChain, LangGraph, PostgreSQL (verified in the Docker phase), Docker, GitHub Actions.

## Directory structure
_TODO (Phase 10)_

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

## Database

SQLite by default (`DATABASE_URL=sqlite:///./workflow_agent.db`); the repository layer is
backend-agnostic so Postgres is a configuration change (verified in the Docker phase, not before).

```bash
alembic upgrade head     # create/upgrade the schema
alembic downgrade base   # tear it down
```

Tables: `workflows`, `workflow_events`, `tool_executions`, `approvals`.
Design notes:
- Repositories never commit; callers own the transaction (`session_scope`).
- Workflow status changes go through an explicit state machine; terminal states are final.
- Approval decisions are a conditional `UPDATE ... WHERE status='pending'`, so a duplicate or
  concurrent decision can succeed only once. A partial unique index allows one pending approval per workflow.
- `tool_executions.idempotency_key` is unique, so a retried tool call cannot be recorded twice.
- A test fails if the ORM models and the Alembic migrations drift apart.

## Development checks

```bash
ruff check . && ruff format --check .
mypy
pytest
```

## Sections to be written
How LangGraph is used · How tools work · Human approval flow · API documentation ·
Database design · Testing strategy · Docker setup · CI pipeline · Example workflow ·
Design tradeoffs · Limitations · Future improvements
