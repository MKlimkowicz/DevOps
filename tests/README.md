# Database Tests

This directory contains database tests for the DevOps infrastructure.

## Structure

```
tests/
├── database/
│   └── postgresql/
│       ├── conftest.py
│       ├── docker-compose.yml
│       ├── pytest.ini
│       ├── env.example
│       ├── test_connection.py
│       ├── init-scripts/
│       └── tests/
│           └── functional/
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

If setting up for the first time, copy the example environment file:

```bash
cd tests/database/postgresql
cp env.example .env
```

The `.env` file contains the database configuration with these defaults:
- POSTGRES_USER=postgres
- POSTGRES_PASSWORD=devops-test-password
- POSTGRES_DB=appdb
- POSTGRES_HOST=localhost
- POSTGRES_PORT=5432

Modify these values in `.env` if needed for your environment.

### 3. Start PostgreSQL

The tests will automatically start the Docker container if it's not running:

```bash
cd tests/database/postgresql
docker-compose up -d
```

## Running Tests

### All Tests

```bash
pytest tests/database/postgresql/ -v
```

### Specific Test File

```bash
pytest tests/database/postgresql/tests/functional/test_basic_operations.py -v
```

### Specific Test

```bash
pytest tests/database/postgresql/test_connection.py::test_simple_select_one -v
```

### With Markers

```bash
pytest tests/database/postgresql/ -m functional -v
pytest tests/database/postgresql/ -m "not slow" -v
```

### Parallel Execution

```bash
pytest tests/database/postgresql/ -n auto
```

## Prerequisites

- Docker and docker-compose installed
- Python 3.8+
- Sufficient disk space for PostgreSQL Docker volume

## Troubleshooting

### Container Won't Start

```bash
docker-compose down -v
docker-compose up -d
```

### Connection Issues

Verify container is running:
```bash
docker ps | grep postgres-test
```

Check logs:
```bash
docker logs postgres-test
```

### Port Conflicts

If port 5432 is already in use, modify `.env`:
```
POSTGRES_PORT=5433
``` 