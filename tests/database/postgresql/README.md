# Database Tests

This directory contains comprehensive database tests for the DevOps infrastructure, including functional tests and non-functional tests covering performance, load, reliability, and security.

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
│       │   └── 01_extensions.sql
│       └── tests/
│           ├── functional/
│           │   ├── test_basic_operations.py
│           │   ├── test_transactions.py
│           │   ├── test_joins.py
│           │   └── ...
│           └── non_functional/
│               ├── conftest.py
│               ├── performance/
│               │   ├── test_query_performance.py
│               │   ├── test_bulk_operations.py
│               │   └── test_index_efficiency.py
│               ├── load/
│               │   ├── test_concurrent_connections.py
│               │   ├── test_sustained_load.py
│               │   └── test_stress_scenarios.py
│               ├── reliability/
│               │   ├── test_connection_resilience.py
│               │   ├── test_transaction_integrity.py
│               │   ├── test_data_consistency.py
│               │   └── test_recovery_scenarios.py
│               └── security/
│                   ├── test_sql_injection.py
│                   ├── test_authentication.py
│                   ├── test_authorization.py
│                   └── test_data_protection.py
├── requirements.txt
└── README.md
```

## Test Categories

### Functional Tests
Tests for core database functionality:
- Basic CRUD operations (INSERT, SELECT, UPDATE, DELETE)
- Complex queries (joins, subqueries, CTEs)
- Transactions and constraints
- Triggers, views, and stored procedures
- Indexes and query optimization
- JSON operations and window functions
- Set operations and aggregations

### Non-Functional Tests

#### Performance Tests
Benchmark and optimize database performance:
- Query performance (indexed vs unindexed)
- Bulk operations (inserts, updates, deletes)
- Index efficiency (B-tree, Hash, GIN, GiST)
- Aggregation operations
- Full-text search performance
- JSON/JSONB query performance

#### Load Tests
Test database under concurrent load:
- Concurrent connections (scalability testing)
- Connection pool behavior
- Concurrent reads and writes
- Mixed workloads
- Sustained load operations
- Transaction throughput measurement
- Response time percentiles
- Stress scenarios and edge cases
- Deadlock detection

#### Reliability Tests
Verify database resilience and recovery:
- Connection resilience and retry logic
- Transaction integrity (ACID compliance)
- Rollback and savepoint consistency
- Transaction isolation levels
- Data consistency under load
- Constraint enforcement
- Trigger reliability
- Recovery after failures
- Query cancellation

#### Security Tests
Validate security measures:
- SQL injection prevention
- Authentication and access control
- Authorization and privilege management
- Row-level security (RLS)
- Schema and table access control
- Function execution permissions
- Password storage (bcrypt)
- Audit logging
- Prepared statement security

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `pytest==8.0.0` - Test framework
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `pytest-benchmark==4.0.0` - Performance benchmarking
- `locust==2.20.0` - Load testing capabilities
- `psutil==5.9.8` - System resource monitoring
- `faker==22.0.0` - Test data generation
- `pytest-asyncio==0.23.3` - Async test support
- `pytest-xdist==3.5.0` - Parallel test execution
- `python-dotenv==1.0.0` - Environment configuration

### 2. Configure Environment

```bash
cd tests/database/postgresql
cp env.example .env
```

Configuration variables:
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=devops-test-password`
- `POSTGRES_DB=appdb`
- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5432`

### 3. Start PostgreSQL

```bash
docker-compose up -d
```

The tests will automatically start the container if not running.

## Running Tests

### All Tests

```bash
pytest tests/database/postgresql/ -v
```

### By Category

```bash
# Functional tests
pytest tests/database/postgresql/tests/functional/ -v

# Non-functional tests
pytest tests/database/postgresql/tests/non_functional/ -v

# Specific category
pytest tests/database/postgresql/tests/non_functional/performance/ -v
```

### By Test File

```bash
pytest tests/database/postgresql/tests/functional/test_basic_operations.py -v
```

### Specific Test

```bash
pytest tests/database/postgresql/test_connection.py::test_simple_select_one -v
```

### Using Markers

```bash
# Performance tests (benchmarks, query optimization)
pytest tests/database/postgresql/ -m performance -v

# Load tests (concurrent connections, stress testing)
pytest tests/database/postgresql/ -m load -v

# Reliability tests (resilience, recovery)
pytest tests/database/postgresql/ -m reliability -v

# Security tests (injection, authentication, authorization)
pytest tests/database/postgresql/ -m security -v

# Exclude slow tests (quick CI runs)
pytest tests/database/postgresql/ -m "not slow" -v

# Combined markers
pytest tests/database/postgresql/ -m "security or reliability" -v
```

### Parallel Execution

```bash
pytest tests/database/postgresql/ -n auto
pytest tests/database/postgresql/ -n 4 --dist loadgroup
```

## Test Execution Guidelines

### Development Environment

```bash
# Quick validation (fast tests only)
pytest tests/database/postgresql/ -m "not slow" -v

# Full functional suite
pytest tests/database/postgresql/tests/functional/ -v

# Security checks
pytest tests/database/postgresql/tests/non_functional/security/ -v
```

### CI/CD Pipeline

```bash
# Critical path (functional + security)
pytest tests/database/postgresql/ -m "functional or security" -v

# Performance baseline tracking
pytest tests/database/postgresql/tests/non_functional/performance/ --benchmark-only

# Full suite with parallel execution
pytest tests/database/postgresql/ -n auto --dist loadgroup
```

### Performance Benchmarking

```bash
# Run with benchmark comparison
pytest tests/database/postgresql/tests/non_functional/performance/ --benchmark-compare

# Save benchmark baseline
pytest tests/database/postgresql/tests/non_functional/performance/ --benchmark-save=baseline

# Generate benchmark histogram
pytest tests/database/postgresql/tests/non_functional/performance/ --benchmark-histogram
```

## Non-Functional Test Details

### Performance Tests
Location: `tests/non_functional/performance/`

**test_query_performance.py**
- Indexed vs unindexed query comparison
- Multi-table join performance (2-4 way joins)
- Aggregation operations (GROUP BY, COUNT, SUM, AVG)
- Full-text search with pg_trgm extension
- JSON/JSONB field extraction and filtering

**test_bulk_operations.py**
- Bulk insert operations
- Bulk update and delete operations
- COPY vs INSERT performance comparison

**test_index_efficiency.py**
- B-tree index performance
- Hash index for equality operations
- GIN index for JSONB queries
- GiST index for full-text search
- Index size overhead analysis

### Load Tests
Location: `tests/non_functional/load/`

**test_concurrent_connections.py**
- Maximum concurrent connections testing
- Connection pool exhaustion scenarios
- Concurrent read operations
- Concurrent write operations
- Mixed workload (reads/writes/updates)

**test_sustained_load.py**
- Sustained read load over time
- Sustained write load over time
- Transaction throughput (TPS) measurement
- Response time percentiles (p50, p95, p99)

**test_stress_scenarios.py**
- Rapid connection cycling
- Large result set handling
- Complex queries under load
- Deadlock detection and recovery

### Reliability Tests
Location: `tests/non_functional/reliability/`

**test_connection_resilience.py**
- Connection retry logic
- Timeout handling
- Idle connection keepalive
- Connection pool recovery

**test_transaction_integrity.py**
- Rollback consistency
- Savepoint recovery
- Transaction isolation levels
- Long-running transactions

**test_data_consistency.py**
- Constraint enforcement (foreign keys, checks, unique)
- Trigger reliability under concurrent load
- CASCADE operations (DELETE, UPDATE)
- Data integrity after errors

**test_recovery_scenarios.py**
- Connection recovery after container restart
- Query cancellation handling
- Prepared statement lifecycle

### Security Tests
Location: `tests/non_functional/security/`

**test_sql_injection.py**
- Parameterized query protection
- SELECT injection prevention
- INSERT injection prevention
- UPDATE injection prevention
- UNION-based injection attempts
- Blind injection attempts
- Stored procedure injection

**test_authentication.py**
- Invalid credentials handling
- Password requirement enforcement
- Privilege escalation prevention
- SSL/TLS connection support

**test_authorization.py**
- Table access control
- Schema-level permissions
- Function execution privileges
- Row-level security (RLS) policies

**test_data_protection.py**
- Sensitive data handling
- Password storage with bcrypt
- Security audit logging
- Prepared statement security

## Performance Expectations

### Typical Run Times
Development environment (2 CPU cores, 2GB RAM):

| Test Suite | Duration | Notes |
|------------|----------|-------|
| Functional | 2-3 min | CRUD, joins, transactions |
| Performance | 2-3 min | Includes benchmark iterations |
| Load | 3-5 min | Concurrent operations, sustained load |
| Reliability | 1-2 min | Connection resilience, recovery |
| Security | 30-60s | Injection prevention, auth |
| **Full Suite** | **8-12 min** | All categories combined |

### Quick Test Runs
- Functional only: ~2 minutes
- Security only: ~30 seconds
- Non-slow tests: ~3 minutes

### Resource Requirements
- Docker container: 2GB RAM, 2 CPU cores
- Test execution: ~500MB RAM
- Temporary disk: ~1GB for test data

## Prerequisites

### Required
- Docker 20.10+ and docker-compose 1.29+
- Python 3.8+ (3.10+ recommended)
- 4GB available RAM (for concurrent testing)
- 10GB disk space (Docker volume + test data)

### Recommended for Load Testing
- 8GB RAM for high concurrent connections
- SSD for improved I/O performance
- Stable network connection

## Troubleshooting

### Container Issues

**Container won't start:**
```bash
docker-compose down -v
docker-compose up -d
```

**Connection issues:**
```bash
docker ps | grep postgres-test
docker logs postgres-test
```

**Port conflicts:**
```bash
# Modify .env file
POSTGRES_PORT=5433
```

### Performance Test Issues

**Slow benchmark tests:**
```bash
pytest tests/non_functional/performance/ --benchmark-max-time=1
```

**Out of memory during bulk operations:**
- Reduce test data size in large_dataset fixture
- Increase Docker memory limit in docker-compose.yml

### Load Test Issues

**Connection limit exceeded:**
```bash
# Check max_connections
docker exec postgres-test psql -U postgres -c "SHOW max_connections;"

# Increase limit in docker-compose.yml
command: -c max_connections=200
```

**Deadlock in concurrent tests:**
- Expected behavior for deadlock_scenarios test
- Retry logic handles automatically

### Security Test Issues

**Restricted user creation fails:**
- Ensure test user has sufficient privileges
- Check for conflicting existing users

**RLS tests skipped:**
- Row-level security requires PostgreSQL 9.5+
- Verify pgcrypto extension is installed

## Contributing

### Adding Tests

1. Place functional tests in `tests/functional/`
2. Place non-functional tests in appropriate category directory
3. Use existing fixtures from `conftest.py`
4. Add appropriate pytest markers
5. Include concise docstring explaining test purpose
6. Follow naming convention: `test_*`

### Code Style

- No inline comments (code should be self-documenting)
- Docstrings only for test functions and complex fixtures
- Use parameterized queries for all SQL operations
- Clean up resources in fixture teardown

### Performance Considerations

- Mark slow tests with `@pytest.mark.slow`
- Use benchmark fixture for performance tests
- Minimize test data size for quick iteration
- Ensure tests are parallel-safe (no shared state)

### Test Markers

Available markers:
- `@pytest.mark.functional` - Functional database tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.load` - Load and stress tests
- `@pytest.mark.reliability` - Reliability and resilience tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.slow` - Long-running tests
