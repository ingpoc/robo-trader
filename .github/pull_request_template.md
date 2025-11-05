## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactoring (code changes that neither fix a bug nor add a feature)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Security fix
- [ ] Dependency update

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Relates to #

## Changes Made

<!-- Provide a bullet-point list of changes -->

-
-
-

## Testing

<!-- Describe the testing you've done -->

### Backend Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests passing locally (`pytest`)

### Frontend Testing

- [ ] Unit tests added/updated
- [ ] E2E tests added/updated (Playwright)
- [ ] Manual testing in browser completed
- [ ] All tests passing locally (`npm run test`)

### Test Coverage

- Current coverage: ___%
- Coverage change: +/- ___%

## Checklist

### Code Quality

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] Code is formatted (Python: `black`, Frontend: `prettier`)
- [ ] Linting passes (Python: `ruff`, Frontend: `eslint`)
- [ ] Type checking passes (Python: `mypy`, Frontend: `tsc`)

### Architecture & Best Practices

- [ ] I have read the relevant CLAUDE.md files for the layers I'm modifying
- [ ] My changes follow the coordinator-based monolithic architecture pattern
- [ ] I'm using dependency injection (not global state)
- [ ] I'm using event-driven communication where appropriate
- [ ] I'm using async/await for all I/O operations
- [ ] Database operations use locked ConfigurationState methods (no direct DB access)
- [ ] All Claude SDK calls go through the AI_ANALYSIS queue (no direct calls)
- [ ] Error handling uses custom exception types with rich context
- [ ] Files respect modularization limits (max 350 lines, max 10 methods/class)

### Testing & Validation

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have tested the changes in a browser (for frontend changes)
- [ ] I have tested API endpoints (for backend changes)
- [ ] No errors in browser console or backend logs
- [ ] Database migrations tested (if applicable)

### Documentation

- [ ] I have updated the documentation accordingly
- [ ] I have updated CLAUDE.md files if adding new patterns
- [ ] I have added/updated docstrings for new/modified functions
- [ ] I have updated README.md if needed

### Security & Performance

- [ ] No secrets or API keys in code
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Performance impact considered and optimized
- [ ] Rate limiting considered (if applicable)

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

### Before

<!-- Screenshot before changes -->

### After

<!-- Screenshot after changes -->

## Deployment Notes

<!-- Any special deployment considerations? Database migrations? Environment variables? -->

- [ ] No special deployment steps required
- [ ] Database migration required: <!-- describe -->
- [ ] New environment variables required: <!-- list them -->
- [ ] Configuration changes required: <!-- describe -->
- [ ] Dependencies updated: <!-- list critical dependencies -->

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Improved performance: <!-- describe -->
- [ ] May impact performance: <!-- describe and justify -->

## Rollback Plan

<!-- How to rollback if this deployment causes issues? -->

## Additional Context

<!-- Add any other context about the PR here -->

---

**For Reviewers:**

- [ ] Code review completed
- [ ] Architecture review completed
- [ ] Security review completed
- [ ] Tests reviewed and passing
- [ ] Documentation reviewed
- [ ] Deployment plan reviewed
