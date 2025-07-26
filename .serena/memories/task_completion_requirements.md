# Task Completion Requirements

## When Tasks Are Completed

According to CLAUDE.md development rules, after every task implementation that works:

### Required Actions
1. **Run the application** to check if it works
2. **Fix all issues** if any are found
3. **Commit the code** after every task implemented (if it works)
4. **Update task progress** in `./plans/<FEATURE_NAME>_TASKS.md`

### Code Quality Checks
When available, run these commands before committing:
```bash
# Linting (when configured)
black app/
flake8 app/

# Type checking (if configured)
mypy app/

# Tests (when available)
pytest
```

### Health Verification
```bash
# Test API health
curl http://localhost:8000/health

# Check service status
docker-compose ps

# View recent logs
docker-compose logs --tail=50 devpocket-api
```

### Commit Guidelines
- **Keep commits focused** on actual code changes
- **NEVER add AI attribution signatures** (explicitly forbidden in CLAUDE.md)
- **Use conventional commit format**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- **Create clean, professional commit messages** without AI references

### Documentation Updates
- Update relevant `./plans/<FEATURE_NAME>_TASKS.md` files
- Mark completed tasks as `[x]`
- Add new discovered tasks if needed
- Update status section when feature is complete

### Error Handling Requirements
- Implement error catch handlers carefully
- Add validation for all inputs
- Follow security best practices
- Focus on human-readable & developer-friendly code
- Maintain high standard of user experience
