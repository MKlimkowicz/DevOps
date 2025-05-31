#!/bin/bash
set -e

echo "🔍 Testing PostgreSQL connectivity..."

# Get the database password
POSTGRES_PASSWORD=$(aws ssm get-parameter --name "/devops/dev/postgres/password" --with-decryption --query 'Parameter.Value' --output text)
DB_HOST="10.0.20.80"
DB_PORT="30432"

echo "📍 Testing connection to PostgreSQL at $DB_HOST:$DB_PORT"

# Test basic connectivity with timeout
if timeout 10 bash -c "</dev/tcp/$DB_HOST/$DB_PORT"; then
    echo "✅ Port $DB_PORT is reachable on $DB_HOST"
else
    echo "❌ Cannot reach port $DB_PORT on $DB_HOST"
    echo "This may be due to security group restrictions or instance not ready"
    exit 1
fi

# Test with psql if available
if command -v psql >/dev/null 2>&1; then
    echo "🔧 Testing with psql..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d appdb -c "SELECT version();" -c "SELECT COUNT(*) as sample_count FROM sample_metrics;"
else
    echo "⚠️  psql not available locally, but port connectivity test passed"
    echo "To test SQL connectivity, run this on an instance with psql:"
    echo "PGPASSWORD='[password]' psql -h $DB_HOST -p $DB_PORT -U postgres -d appdb -c 'SELECT version();'"
fi

echo "✅ PostgreSQL connectivity test completed" 