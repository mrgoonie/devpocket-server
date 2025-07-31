# Cluster Tests Fix Tasks

## Overview
Fix 48 failing cluster-related tests to achieve stable test coverage. Issues identified:

### 1. Model Validation Issues
- [x] **Fix ClusterRegion enum validation**: Tests expect 'us-west-2' but enum uses 'us-west'
- [ ] **Add missing required fields**: endpoint, encrypted_kube_config, created_by in model creation
- [x] **Fix provider field**: Tests use 'provider' field but ClusterBase doesn't have it

### 2. Missing ClusterService Methods
- [x] **Add get_cluster() method**: Tests expect this instead of get_cluster_by_id()
- [x] **Add _encrypt_kube_config() method**: For encryption operations
- [x] **Add _decrypt_kube_config() method**: For decryption operations
- [x] **Add _validate_kube_config() method**: For validation operations
- [x] **Add get_regions_by_provider() method**: Filter regions by provider
- [x] **Add get_default_cluster() method**: Get default cluster across all regions
- [x] **Add set_default_cluster() method**: Set a cluster as default
- [x] **Add get_available_regions() method**: Return static list of regions

### 3. Async/Await Issues
- [x] **Fix list_clusters() return type**: Should return List[ClusterInDB] not List[ClusterResponse]
- [x] **Fix async iteration**: Tests expect `.to_list()` method on cursor
- [ ] **Fix kubernetes config loading**: Replace non-existent `load_config_from_dict`

### 4. Mock and Test Configuration Issues
- [x] **Fix AsyncMock usage**: Ensure proper async behavior in tests
- [x] **Update test data**: Match expected model structure (added defaults for missing fields)
- [x] **Fix ObjectId validation**: Handle string IDs in tests properly
- [ ] **Fix coroutine handling**: Properly await async operations

### 5. Model Structure Updates
- [x] **Add provider field to ClusterBase**: Tests expect this field
- [x] **Update ClusterRegion enum**: Add proper region mappings
- [x] **Fix required field validation**: Make endpoint optional in creates, required in DB

### 6. Current Status (Progress Update)
- **Passed**: 18/26 tests (69.2% improvement from 4/26)
- **Remaining Issues**: 8 failed tests - Health check tests (kubernetes mock issues), some delete operations, async mocking
- **Recent Fixes**: List operations, region methods, ObjectId handling, model validation

### 6. Implementation Priority
1. Update models to match test expectations
2. Add missing service methods with proper signatures
3. Fix async operation handling
4. Update test mocking configuration
5. Run tests to verify fixes

## Expected Outcome
- All 48 cluster tests pass
- Maintain existing test coverage above 50%
- Clean, maintainable implementation matching project patterns
