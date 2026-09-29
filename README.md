# Workflow Automation Agent

An Issue-to-Resolution workflow automation system built with FastAPI, LangChain, and LangGraph.
A user submits a software issue; the system classifies it, searches a local knowledge base,
proposes a remediation plan, pauses for human approval when the action is risky, executes
allowlisted tools, validates the result, and persists the full execution history.

> **Status: under construction (Phase 1 of 10 complete).** Sections marked _TODO_ are filled in
> as the corresponding phase is implemented. Nothing here describes a feature that is not
> implemented and tested.

## Problem statement
_TODO (Phase 10)_

## Architecture
_TODO (Phase 10) — see the design in the project plan: API → services → LangGraph → tools/repositories → database._

## Workflow diagram
_TODO (Phase 4/10)_

## Tech stack
Implemented so far: Python 3.11+, FastAPI, Pydantic v2 / pydantic-settings, structlog, pytest, ruff, mypy.
Planned: LangChain, LangGraph, SQLAlchemy + Alembic, PostgreSQL, Docker, GitHub Actions.

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
