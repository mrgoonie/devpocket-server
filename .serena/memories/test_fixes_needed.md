# Test Fixes Required

## WebSocket Manager Issues
1. ✅ Added `broadcast_to_user` method - broadcasts message to all user connections
2. ✅ Added `get_user_connection_count` method - returns count of user connections

## Auth Service Issues
3. Fix `_handle_failed_login` method - async mock issue with database calls
4. Fix `authenticate_user` with locked account test - missing email field in mock data
5. Fix `generate_email_verification_token` test - secrets import issue
6. Fix `verify_email_token` with expired token - logic issue
7. Fix Google login tests - missing 'iss' field in mock token data

## Auth API Issues
8. Fix email verification validation - should return 422 for invalid data
9. Fix resend verification email - currently returns 403 instead of expected codes
10. Fix login validation errors - should return 422 for missing fields

## Test Data Issues
- Mock user documents missing required fields (email, etc.)
- Google token mock data missing required fields (iss, etc.)
- Async mock setup issues in service tests
