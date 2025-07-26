#!/bin/bash

# Test runner script for DevPocket Server
# Usage: ./scripts/run-tests.sh [test-type] [options]

set -e

TEST_TYPE=${1:-all}
DOCKER_COMPOSE_FILE="docker-compose.test.yml"

echo "🧪 Running DevPocket Server Tests..."
echo "📋 Test Type: $TEST_TYPE"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to cleanup test containers
cleanup() {
    echo "🧹 Cleaning up test containers..."
    docker-compose -f $DOCKER_COMPOSE_FILE down -v --remove-orphans 2>/dev/null || true
    docker system prune -f --volumes --filter label=test=devpocket 2>/dev/null || true
}

# Function to run tests in container
run_tests_in_container() {
    local test_cmd="$1"

    echo "🏗️  Building test environment..."
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

    echo "🚀 Starting test dependencies..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d mongo-test redis-test

    # Wait for dependencies to be ready
    echo "⏳ Waiting for dependencies..."
    sleep 10

    echo "🧪 Running tests..."
    docker-compose -f $DOCKER_COMPOSE_FILE run --rm test-runner $test_cmd

    local exit_code=$?

    echo "📊 Test Results:"
    if [ $exit_code -eq 0 ]; then
        echo "✅ All tests passed!"
    else
        echo "❌ Some tests failed (exit code: $exit_code)"
    fi

    return $exit_code
}

# Function to run tests locally
run_tests_locally() {
    local test_cmd="$1"

    echo "🏠 Running tests locally..."

    # Check if virtual environment exists
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        echo "🐍 Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # Install dependencies
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    pip install -r requirements-test.txt

    # Start local dependencies
    echo "🚀 Starting local dependencies..."
    docker-compose up -d mongo redis

    # Wait for dependencies
    echo "⏳ Waiting for dependencies..."
    sleep 5

    # Run tests
    echo "🧪 Running tests..."
    eval $test_cmd

    local exit_code=$?

    # Stop dependencies
    docker-compose stop mongo redis

    return $exit_code
}

# Main execution
main() {
    check_docker

    # Set test command based on type
    case $TEST_TYPE in
        "unit")
            TEST_CMD="pytest tests/ -m 'unit' -v"
            ;;
        "integration")
            TEST_CMD="pytest tests/ -m 'integration' -v"
            ;;
        "auth")
            TEST_CMD="pytest tests/test_auth.py -v"
            ;;
        "health")
            TEST_CMD="pytest tests/test_health.py -v"
            ;;
        "environments")
            TEST_CMD="pytest tests/test_environments.py -v"
            ;;
        "coverage")
            TEST_CMD="pytest tests/ --cov=app --cov-report=html --cov-report=term"
            ;;
        "fast")
            TEST_CMD="pytest tests/ -x --tb=short"
            ;;
        "all")
            TEST_CMD="pytest tests/ -v"
            ;;
        "local")
            shift
            TEST_CMD="pytest tests/ $@"
            run_tests_locally "$TEST_CMD"
            exit $?
            ;;
        *)
            echo "Usage: $0 [test-type] [options]"
            echo ""
            echo "Test types:"
            echo "  all         - Run all tests (default)"
            echo "  unit        - Run unit tests only"
            echo "  integration - Run integration tests only"
            echo "  auth        - Run authentication tests"
            echo "  health      - Run health check tests"
            echo "  environments - Run environment tests"
            echo "  coverage    - Run tests with coverage report"
            echo "  fast        - Run tests with fast failure"
            echo "  local       - Run tests locally (not in Docker)"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests in Docker"
            echo "  $0 auth              # Run auth tests in Docker"
            echo "  $0 local -v          # Run all tests locally with verbose output"
            echo "  $0 coverage          # Run tests with coverage report"
            exit 1
            ;;
    esac

    # Trap cleanup on exit
    trap cleanup EXIT

    # Run tests in container
    run_tests_in_container "$TEST_CMD"
    exit_code=$?

    # Copy coverage report if generated
    if [[ "$TEST_TYPE" == "coverage" ]]; then
        echo "📊 Copying coverage report..."
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm --no-deps test-runner tar -czf - htmlcov/ | tar -xzf - 2>/dev/null || true
        echo "📊 Coverage report available in htmlcov/index.html"
    fi

    exit $exit_code
}

# Run main function
main "$@"
