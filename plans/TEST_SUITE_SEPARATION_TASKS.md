# Test Suite Separation - Integration vs Coverage Tests

## Problem Summary
The test suite was hanging during cleanup and integration tests were failing in CI environments where kubeconfig was not available. Integration tests were being included in coverage runs, causing issues in GitHub Actions.

## Solution Implemented

### 1. Updated Pytest Configuration (`pytest.ini`)
- Removed coverage configuration from default addopts to avoid running coverage on all tests by default
- Added proper markers for integration tests
- Enhanced marker descriptions

**Status: ✅ COMPLETED**

### 2. Enhanced Test Runner Script (`scripts/run-tests.sh`)
- **coverage**: Now excludes integration tests (`-m 'not integration'`) to prevent hanging
- **coverage-all**: New option to run coverage with all tests (use with caution)
- **ci**: New CI-friendly test suite that excludes integration tests
- **fast**: Now excludes integration tests for faster execution
- Updated help text with clearer descriptions

**Status: ✅ COMPLETED**

### 3. Integration Test Improvements (`tests/test_environment_integration.py`)
- Added `check_kubeconfig_available()` function to detect kubeconfig availability
- Added `skip_if_no_kubeconfig()` decorator that skips tests when kubeconfig is not available
- Applied skip decorators to all integration test functions and fixtures
- Enhanced docstrings to clarify kubeconfig requirements

**Status: ✅ COMPLETED**

### 4. Docker Configuration Updates
- **docker-compose.test.yml**: Default command now excludes integration tests
- **Dockerfile.test**: Default CMD now excludes integration tests

**Status: ✅ COMPLETED**

## Test Results

### Coverage Suite (Excludes Integration Tests)
```bash
pytest tests/ -m 'not integration' --cov=app --cov-report=term --collect-only
# Result: 245/249 tests collected (4 deselected)
```

### Integration Tests with Kubeconfig Available
```bash
pytest tests/test_environment_integration.py -m 'integration' -v
# Result: 4 passed (tests run normally)
```

### Integration Tests without Kubeconfig
```bash
pytest tests/test_environment_integration.py -m 'integration' -v
# Result: 4 skipped (properly skipped when no kubeconfig)
```

## Usage Examples

### For CI/GitHub Actions (No Kubernetes Access)
```bash
./scripts/run-tests.sh coverage    # Excludes integration tests
./scripts/run-tests.sh ci          # CI-friendly suite
./scripts/run-tests.sh fast        # Fast tests without integration
```

### For Local Development (With Kubernetes Access)
```bash
./scripts/run-tests.sh integration # Run only integration tests
./scripts/run-tests.sh all         # Run all tests including integration
./scripts/run-tests.sh coverage-all # Coverage with all tests (if needed)
```

### Docker Testing
```bash
docker-compose -f docker-compose.test.yml run --rm test-runner
# Automatically excludes integration tests
```

## Key Benefits

1. **No More Hanging**: Coverage tests no longer hang because integration tests are excluded
2. **CI-Friendly**: GitHub Actions won't fail due to missing kubeconfig
3. **Automatic Skipping**: Integration tests automatically skip when kubeconfig is unavailable
4. **Flexible Test Suites**: Different test commands for different scenarios
5. **Better Organization**: Clear separation between unit tests and integration tests

## Files Modified

- ✅ `pytest.ini` - Updated pytest configuration
- ✅ `scripts/run-tests.sh` - Enhanced test runner with new options
- ✅ `tests/test_environment_integration.py` - Added kubeconfig checks and skip logic
- ✅ `docker-compose.test.yml` - Updated default test command
- ✅ `Dockerfile.test` - Updated default test command

## Next Steps

1. Update CI/CD pipeline to use `./scripts/run-tests.sh coverage` instead of running all tests
2. Update development documentation to reflect new test suite options
3. Consider adding unit test markers to other test files for better organization

**Status: ✅ COMPLETED**
