#!/bin/bash

# Test runner script for DevPocket Server
# Usage: ./scripts/run-tests.sh [test-type] [options]

set -e

TEST_TYPE=${1:-all-unit}
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
    local use_integration_runner="$2"

    echo "🏗️  Building test environment..."
    # Remove --no-cache to allow Docker layer caching for faster builds
    # Use optimized build process
    docker-compose -f $DOCKER_COMPOSE_FILE build

    echo "🚀 Starting test dependencies..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d mongo-test redis-test

    # Wait for dependencies to be ready
    echo "⏳ Waiting for dependencies..."
    sleep 10

    echo "🧪 Running tests..."
    if [ "$use_integration_runner" = "true" ]; then
        echo "Using integration test runner..."
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm integration-test-runner sh -c "$test_cmd"
    else
        echo "Using standard test runner..."
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm test-runner sh -c "$test_cmd"
    fi

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
            # Run all tests except those marked as integration
            TEST_CMD='pytest tests/ -m "not integration" -v --tb=short'
            ;;
        "integration")
            TEST_CMD='pytest tests/ -m integration -v -s --tb=short --maxfail=3'
            ;;
        "auth")
            # Run auth tests that are not integration tests
            TEST_CMD='pytest tests/test_auth.py tests/test_services_auth.py tests/test_middleware_auth.py -v --tb=short -m "not integration"'
            ;;
        "health")
            TEST_CMD="pytest tests/test_health.py -v --tb=short"
            ;;
        "environments")
            # Run environment tests but exclude integration tests
            TEST_CMD="pytest tests/test_environments.py -v --tb=short"
            ;;
        "websocket")
            # Run WebSocket tests but exclude integration tests
            TEST_CMD='pytest tests/test_websocket.py tests/test_api_websocket.py -v --tb=short -m "not integration"'
            ;;
        "service")
            # Run service layer tests but exclude integration tests
            TEST_CMD='pytest tests/test_services_*.py -v --tb=short -m "not integration"'
            ;;
        "api")
            # Run API tests but exclude integration tests
            TEST_CMD='pytest tests/test_api_*.py -v --tb=short -m "not integration"'
            ;;
        "env-integration")
            TEST_CMD="pytest tests/test_environment_integration.py -v -s --tb=short --maxfail=1"
            ;;
        "coverage")
            # Exclude integration tests from coverage to prevent hanging
            TEST_CMD='pytest tests/ -m "not integration" --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=70 --tb=short'
            ;;
        "coverage-integration")
            # Run integration tests with coverage (use with caution - may hang)
            TEST_CMD='pytest tests/ -m integration --cov=app --cov-append --cov-report=html --cov-report=term-missing --tb=short --maxfail=1'
            ;;
        "coverage-all")
            # Run all tests with coverage (excluding integration to prevent hanging)
            TEST_CMD='pytest tests/ -m "not integration" --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml --cov-fail-under=70 --tb=short'
            ;;
        "fast")
            # Fast tests exclude integration and slow tests
            TEST_CMD='pytest tests/ -m "not integration and not slow" -x --tb=line'
            ;;
        "smoke")
            # Smoke tests - minimal test suite for quick validation
            TEST_CMD="pytest tests/test_health.py tests/test_auth.py::test_register_user -v --tb=short"
            ;;
        "ci")
            # CI-friendly test suite that excludes integration tests
            TEST_CMD='pytest tests/ -m "not integration" -v --tb=short --maxfail=5'
            ;;
        "all")
            # Run all tests but limit integration test failures
            TEST_CMD="pytest tests/ -v --tb=short --maxfail=10"
            ;;
        "all-unit")
            # Run all unit tests (safer than 'all')
            TEST_CMD='pytest tests/ -m "not integration" -v --tb=short'
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
            echo "  all-unit    - Run all unit tests (excludes integration tests) - RECOMMENDED"
            echo "  all         - Run all tests including integration (may hang - use with caution)"
            echo "  unit        - Run unit tests only"
            echo "  integration - Run integration tests only (requires Kubernetes)"
            echo "  auth        - Run authentication tests (unit only)"
            echo "  health      - Run health check tests"
            echo "  environments - Run environment tests (unit only)"
            echo "  websocket   - Run WebSocket tests (unit only)"
            echo "  service     - Run service layer tests (unit only)"
            echo "  api         - Run API endpoint tests (unit only)"
            echo "  env-integration - Run environment integration tests (requires Kubernetes)"
            echo ""
            echo "Coverage types:"
            echo "  coverage    - Run unit tests with coverage report (recommended)"
            echo "  coverage-all - Run all unit tests with coverage (XML + HTML reports)"
            echo "  coverage-integration - Run integration tests with coverage (use with caution)"
            echo ""
            echo "Development types:"
            echo "  fast        - Run fast tests only (excludes integration and slow tests)"
            echo "  smoke       - Run minimal smoke tests for quick validation"
            echo "  ci          - CI-friendly test suite (unit tests only)"
            echo "  local       - Run tests locally (not in Docker)"
            echo ""
            echo "Examples:"
            echo "  $0                       # Run all-unit tests (recommended default)"
            echo "  $0 all-unit             # Run all unit tests safely"
            echo "  $0 auth                 # Run auth unit tests in Docker"
            echo "  $0 integration          # Run integration tests (requires kubeconfig)"
            echo "  $0 coverage             # Run coverage on unit tests (recommended)"
            echo "  $0 fast                 # Run fast tests for development"
            echo "  $0 smoke                # Run minimal smoke tests"
            echo "  $0 local -v             # Run all tests locally with verbose output"
            echo "  $0 local unit           # Run unit tests locally"
            echo "  $0 ci                   # Run CI-friendly test suite"
            echo ""
            echo "⚠️  WARNING: 'all' and 'coverage-integration' may hang due to K8s cleanup issues."
            echo "   Use 'all-unit' and 'coverage' for safer testing."
            exit 1
            ;;
    esac

    # Override default for backward compatibility
    if [ "$TEST_TYPE" = "all" ] && [ $# -eq 0 ]; then
        echo "⚠️  NOTE: Defaulting to 'all-unit' instead of 'all' to prevent hanging."
        echo "    Use './scripts/run-tests.sh all' explicitly to run integration tests."
        TEST_TYPE="all-unit"
        TEST_CMD='pytest tests/ -m "not integration" -v --tb=short'
    fi

    # Determine if we should use integration runner
    USE_INTEGRATION_RUNNER="false"
    if [[ "$TEST_TYPE" == "integration" ]] || [[ "$TEST_TYPE" == "env-integration" ]] || [[ "$TEST_TYPE" == "coverage-integration" ]]; then
        USE_INTEGRATION_RUNNER="true"
    fi

    # Trap cleanup on exit
    trap cleanup EXIT

    # Run tests in container
    run_tests_in_container "$TEST_CMD" "$USE_INTEGRATION_RUNNER"
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
