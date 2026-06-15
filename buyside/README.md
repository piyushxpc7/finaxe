# Buyside API Service

A modern, production-ready, asynchronous FastAPI service template. Built with Python 3.11+, SQLAlchemy 2.0 (async), PostgreSQL, Docker containerization, and GitHub Actions CI workflow support.

---

## Features

- **FastAPI Core**: Async route execution with automated Swagger/OpenAPI documentation.
- **SQLAlchemy 2.0 Asyncio**: Type-safe async engine querying and session scope management.
- **Environment Management**: Dynamic Pydantic-based settings configuration.
- **Automated Formatting/Linting**: Configured with Black and Ruff for high-quality, readable, and standardized code.
- **Container Deployment**: Includes a multi-stage Docker build and Docker Compose configuration.
- **Continuous Integration**: Complete GitHub Actions YAML mapping to run testing, styling, and checking pipelines on PRs and commits.

---

## Directory Structure

```text
buyside/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions continuous integration workflow
├── docker/
│   └── README.md              # Containerization reference file
├── src/
│   └── buyside/
│       ├── api/
│       │   ├── endpoints/
│       │   │   ├── health.py  # Service availability endpoints
│       │   │   └── items.py   # Item CRUD endpoints
│       │   │   └── __init__.py
│       │   ├── router.py      # Combines and routes sub-routers
│       │   ├── schemas.py     # Pydantic input/output validation models
│       │   └── __init__.py
│       ├── config/
│       │   └── settings.py    # Environment configuration parser
│       ├── db/
│       │   ├── base.py        # Declarative SQLAlchemy base model
│       │   ├── models.py      # SQLAlchemy DB models definition
│       │   └── session.py     # Async engine and session provider
│       └── main.py            # FastAPI main entrypoint and middlewares setup
├── tests/
│   ├── conftest.py            # Event loop and database mocks
│   ├── test_health.py         # Unit tests checking health status
│   └── test_items.py          # Unit tests checking item CRUD lifecycle
├── .env.example               # Environment template variables file
├── Dockerfile                 # Multi-stage release image definition
├── docker-compose.yml         # Local database and application stack compositor
├── Makefile                   # Simplifies routine commands execution
└── pyproject.toml             # Poetry project packaging and dependencies configuration
```

---

## Prerequisites

Ensure you have the following installed locally:
- Python 3.11+
- [Poetry](https://python-poetry.org/)
- Docker & Docker Compose (optional, for containerized database and app launch)

---

## Quickstart

### Local Setup (Using Poetry)

1. Clone or navigate to the workspace directory.
2. Initialize environment file:
   ```bash
   cp .env.example .env
   ```
3. Install project dependencies and development tools:
   ```bash
   make install
   ```
4. Start the API locally:
   ```bash
   make run
   ```
   The application will run on [http://localhost:8000](http://localhost:8000). You can explore the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### Containerized Environment (Docker Compose)

Launch the entire stack (web application + PostgreSQL database) with a single command:
```bash
make docker-up
```

- Web App is accessible at [http://localhost:8000](http://localhost:8000)
- Database runs on port `5432` with credentials specified in `docker-compose.yml`.

To stop the containers:
```bash
make docker-down
```

---

## Testing & Linting

Verify your code functionality and maintain clean formatting rules using the Makefile commands:

### Running Tests
Execute unit and integration tests (which utilize an in-memory async SQLite engine):
```bash
make test
```

### Checking Lint and Style Errors
Run static type inspection and syntax checkers:
```bash
make lint
```

### Auto-formatting Code
Format codebase with Ruff and Black automatically:
```bash
make format
```
