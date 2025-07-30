#!/bin/bash

# Books Management API - Functional Test Runner
# This script runs all functional test scenarios for the Books API

set -e  # Exit on error

echo "📚 Books Management API - Functional Test Runner"
echo "================================================"
echo "⏰ Started at: $(date)"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the DevOps/tests/api_app directory"
    exit 1
fi

# Function to run tests with error handling
run_test_suite() {
    local test_file=$1
    local description=$2
    local scenario_range=$3
    
    echo ""
    echo "🔍 Running: $description ($scenario_range)"
    echo "================================================"
    
    if python -m pytest "$test_file" -v; then
        echo "✅ $description - PASSED"
        return 0
    else
        echo "❌ $description - FAILED"
        return 1
    fi
}

# Install dependencies if needed
echo "🔧 Checking dependencies..."
if ! python -c "import pytest, fastapi, httpx" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Initialize test results
TOTAL_SUITES=0
PASSED_SUITES=0

echo ""
echo "🚀 Starting functional tests..."
echo ""

# Run CRUD Operations Tests (Scenarios 1-12)
if run_test_suite "tests/functional/test_books_crud.py" "CRUD Operations Tests" "Scenarios 1-12"; then
    ((PASSED_SUITES++))
fi
((TOTAL_SUITES++))

# Run Error Handling Tests (Scenarios 13-18)
if run_test_suite "tests/functional/test_books_error_handling.py" "Error Handling Tests" "Scenarios 13-18"; then
    ((PASSED_SUITES++))
fi
((TOTAL_SUITES++))

# Run Advanced Features Tests (Scenarios 19-26)
if run_test_suite "tests/functional/test_books_advanced.py" "Advanced Features Tests" "Scenarios 19-26"; then
    ((PASSED_SUITES++))
fi
((TOTAL_SUITES++))

# Summary
echo ""
echo "📊 TEST SUMMARY"
echo "================================================"
echo "🎯 Results: $PASSED_SUITES/$TOTAL_SUITES test suites passed"
echo "⏰ Completed at: $(date)"

if [ $PASSED_SUITES -eq $TOTAL_SUITES ]; then
    echo "🎉 All test suites passed!"
    exit 0
else
    echo "⚠️  Some test suites failed. Check the output above for details."
    exit 1
fi 