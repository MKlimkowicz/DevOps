# Database Tests

This directory contains database tests for the DevOps infrastructure.

## Structure

```
tests/
├── database/
│   └── postgresql/          # PostgreSQL specific tests
│       ├── conftest.py      # PostgreSQL connection fixtures
│       └── test_connection.py  # Basic connectivity tests
├── requirements.txt         # Test dependencies
└── README.md               # This file
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure AWS credentials are configured:
```bash
aws configure
# or use environment variables:
# export AWS_ACCESS_KEY_ID=your_key
# export AWS_SECRET_ACCESS_KEY=your_secret
# export AWS_DEFAULT_REGION=eu-central-1
```

## Running PostgreSQL Tests

From the project root directory:

```bash
# Run all PostgreSQL tests
pytest tests/database/postgresql/ -v

# Run specific test
pytest tests/database/postgresql/test_connection.py::test_simple_select_one -v
```

## Prerequisites

- AWS credentials with access to Parameter Store
- Network access to PostgreSQL instance (10.0.20.81:30432)
- PostgreSQL instance must be running and accessible

## Future Extensions

- Add `tests/application/` for application-specific tests
- Add `tests/api/` for API tests
- Add `tests/integration/` for integration tests 