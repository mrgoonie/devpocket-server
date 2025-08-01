#!/bin/bash

# Docker test runner with different configurations
# Usage: ./scripts/test-docker.sh [test-type] [integration|unit]

set -e

TEST_TYPE=${1:-all}
TEST_MODE=${2:-unit}
DOCKER_COMPOSE_FILE="docker-compose.test.yml"

echo "🧪 Running Docker Tests..."
echo "📋 Test Type: $TEST_TYPE"
echo "🔧 Test Mode: $TEST_MODE"

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

# Function to run tests with specific configuration
run_tests() {
    local test_cmd="$1"
    local testing_env="$2"

    echo "🏗️  Building test environment..."
    docker-compose -f $DOCKER_COMPOSE_FILE build

    echo "🚀 Starting test dependencies..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d mongo-test redis-test

    # Wait for dependencies to be ready
    echo "⏳ Waiting for dependencies..."
    sleep 10

    echo "🧪 Running tests with TESTING=$testing_env..."
    docker-compose -f $DOCKER_COMPOSE_FILE run --rm \
        -e TESTING=$testing_env \
        test-runner $test_cmd

    local exit_code=$?

    echo "📊 Test Results:"
    if [ $exit_code -eq 0 ]; then
        echo "✅ All tests passed!"
    else
        echo "❌ Some tests failed (exit code: $exit_code)"
    fi

    return $exit_code
}

# Main execution
main() {
    check_docker

    # Set test command and environment based on mode and type
    case $TEST_MODE in
        "integration")
            TESTING_ENV="false"
            case $TEST_TYPE in
                "env")
                    TEST_CMD="pytest tests/test_environment_integration.py -v -s --tb=short"
                    ;;
                "all")
                    TEST_CMD="pytest tests/ -m 'integration' -v -s --tb=short"
                    ;;
                *)
                    TEST_CMD="pytest tests/test_${TEST_TYPE}_integration.py -v -s --tb=short"
                    ;;
            esac
            ;;
        "unit")
            TESTING_ENV="true"
            case $TEST_TYPE in
                "auth")
                    TEST_CMD="pytest tests/test_services_auth.py -v"
                    ;;
                "api")
                    TEST_CMD="pytest tests/test_api*.py -v"
                    ;;
                "all")
                    TEST_CMD="pytest tests/ -m 'not integration' -v"
                    ;;
                *)
                    TEST_CMD="pytest tests/test_${TEST_TYPE}.py -v"
                    ;;
            esac
            ;;
        *)
            echo "❌ Invalid test mode: $TEST_MODE"
            echo "Valid modes: unit, integration"
            exit 1
            ;;
    esac

    # Trap cleanup on exit
    trap cleanup EXIT

    # Run tests
    run_tests "$TEST_CMD" "$TESTING_ENV"
    exit_code=$?

    exit $exit_code
}

# Show usage if no arguments or help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $0 [test-type] [integration|unit]"
    echo ""
    echo "Test types:"
    echo "  all         - Run all tests (default)"
    echo "  auth        - Run authentication tests"
    echo "  api         - Run API tests"
    echo "  env         - Run environment tests"
    echo ""
    echo "Test modes:"
    echo "  unit        - Run unit tests (TESTING=true, mocked operations)"
    echo "  integration - Run integration tests (TESTING=false, real operations)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all unit tests"
    echo "  $0 auth unit           # Run auth unit tests"
    echo "  $0 env integration     # Run environment integration tests"
    echo "  $0 all integration     # Run all integration tests"
    exit 0
fi

# Run main function
main "$@"
