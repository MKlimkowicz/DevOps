"""
Test runner script for Books Management API functional tests.

This script provides an easy way to run all functional test scenarios
with proper reporting and error handling.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (Exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Books API functional tests")
    parser.add_argument("--test-type", choices=["all", "crud", "error", "advanced"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Run tests with verbose output")
    parser.add_argument("--report", action="store_true", 
                       help="Generate HTML test report")
    parser.add_argument("--coverage", action="store_true", 
                       help="Generate coverage report")
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"📚 Books Management API - Functional Test Runner")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Working directory: {os.getcwd()}")
    print()
    
    print("🔧 Checking dependencies...")
    dependencies_cmd = "python -c 'import pytest, fastapi, httpx; print(\"All dependencies available\")'"
    if not run_command(dependencies_cmd, "Checking dependencies"):
        print("❌ Missing dependencies. Please run: pip install -r requirements.txt")
        return 1
    
    base_cmd = "python -m pytest"
    
    if args.verbose:
        base_cmd += " -v"
    
    if args.report:
        base_cmd += " --html=functional_test_report.html --self-contained-html"
    
    if args.coverage:
        base_cmd += " --cov=. --cov-report=html --cov-report=term"
    
    test_commands = []
    
    if args.test_type == "all":
        test_commands = [
            (f"{base_cmd} tests/functional/test_books_crud.py", "CRUD Operations Tests (Scenarios 1-12)"),
            (f"{base_cmd} tests/functional/test_books_error_handling.py", "Error Handling Tests (Scenarios 13-18)"),
            (f"{base_cmd} tests/functional/test_books_advanced.py", "Advanced Features Tests (Scenarios 19-26)")
        ]
    elif args.test_type == "crud":
        test_commands = [
            (f"{base_cmd} tests/functional/test_books_crud.py", "CRUD Operations Tests (Scenarios 1-12)")
        ]
    elif args.test_type == "error":
        test_commands = [
            (f"{base_cmd} tests/functional/test_books_error_handling.py", "Error Handling Tests (Scenarios 13-18)")
        ]
    elif args.test_type == "advanced":
        test_commands = [
            (f"{base_cmd} tests/functional/test_books_advanced.py", "Advanced Features Tests (Scenarios 19-26)")
        ]
    
    results = []
    for cmd, description in test_commands:
        success = run_command(cmd, description)
        results.append((description, success))
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {description}")
    
    print(f"\n🎯 Results: {passed}/{total} test suites passed")
    
    if args.report:
        print(f"📄 HTML report generated: functional_test_report.html")
    
    if args.coverage:
        print(f"📈 Coverage report generated: htmlcov/index.html")
    
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main()) 