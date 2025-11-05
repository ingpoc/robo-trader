# GitHub Workflows

This directory contains GitHub Actions workflows for CI/CD, security scanning, and deployment automation.

## Quick Reference

| Workflow | File | Purpose | Trigger |
|----------|------|---------|---------|
| **CI/CD Pipeline** | `ci.yml` | Code quality, testing, builds | Push, PR |
| **Security Scanning** | `security.yml` | Vulnerability & secret scanning | Push, PR, Weekly |
| **Deployment** | `deploy.yml` | Staging & production deployment | Push to main, Tags |
| ~~Quality Checks~~ | ~~`quality-checks.yml`~~ | **DEPRECATED** - Use `ci.yml` | N/A |

## Documentation

📚 **Complete documentation:** [WORKFLOWS.md](../WORKFLOWS.md)

## Workflow Status

| Check | Status |
|-------|--------|
| CI Pipeline | ![CI](https://github.com/robo-trader/actions/workflows/ci.yml/badge.svg) |
| Security | ![Security](https://github.com/robo-trader/actions/workflows/security.yml/badge.svg) |
| Deploy | ![Deploy](https://github.com/robo-trader/actions/workflows/deploy.yml/badge.svg) |

## Key Features

### CI/CD Pipeline (`ci.yml`)
- ✅ Python linting (black, ruff, isort, mypy)
- ✅ Frontend linting (ESLint, TypeScript)
- ✅ Backend tests (pytest, 70% coverage)
- ✅ Frontend tests (Playwright E2E)
- ✅ Docker build validation
- ✅ Integration testing
- ⏱️ Runtime: ~15-20 minutes

### Security Scanning (`security.yml`)
- ✅ CodeQL analysis (Python, JavaScript)
- ✅ Dependency scanning (Safety, npm audit)
- ✅ Secret scanning (TruffleHog)
- ✅ Container scanning (Trivy)
- ✅ SAST (Bandit)
- ✅ License compliance
- ⏱️ Runtime: ~15-20 minutes

### Deployment (`deploy.yml`)
- ✅ Multi-platform Docker builds
- ✅ GitHub Container Registry
- ✅ Staging deployment
- ✅ Production deployment
- ✅ Automated releases
- ✅ Rollback capability
- ⏱️ Runtime: ~20-30 minutes

## Local Validation

### Validate Workflow Syntax

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Validate workflow files
act -l  # List all workflows
act -n  # Dry run (validate without executing)

# Run specific workflow
act push  # Simulate push event
act pull_request  # Simulate PR event
```

### Validate YAML Syntax

```bash
# Install yamllint
pip install yamllint

# Lint all workflow files
yamllint .github/workflows/
```

## Branch Protection Requirements

### Required Status Checks

For `main` and `develop` branches:

- ✅ `ci-status` (ci.yml)
- ✅ `lint-python`
- ✅ `lint-frontend`
- ✅ `test-backend`
- ✅ `test-frontend`
- ✅ `build-docker`
- ✅ `integration-test`
- ✅ `codeql-analysis` (security.yml)

### Additional Protections

- Require pull request reviews (minimum 1)
- Require branches to be up to date
- Restrict force pushes
- Restrict deletions

## Dependabot

Automated dependency updates are configured in `dependabot.yml`:

- **Python dependencies:** Weekly updates
- **npm dependencies:** Weekly updates
- **Docker images:** Weekly updates
- **GitHub Actions:** Weekly updates

## Templates

### Pull Request Template
Location: `.github/pull_request_template.md`

Includes:
- Description and change type
- Testing checklist
- Architecture compliance
- Security considerations
- Deployment notes

### Issue Templates
Location: `.github/ISSUE_TEMPLATE/`

Templates:
- **Bug Report:** Environment, reproduction steps, logs
- **Feature Request:** Use cases, implementation plan, acceptance criteria

## Secrets Configuration

### Required Secrets

| Secret | Purpose | Scope |
|--------|---------|-------|
| `GITHUB_TOKEN` | Container registry, releases | Automatic |
| `CODECOV_TOKEN` | Code coverage upload | Optional |

### Environment Secrets

**Staging:**
- Database and Redis URLs configured in environment

**Production:**
- Database and Redis URLs configured in environment
- Requires manual approval for deployment

## Monitoring

### View Workflow Runs
- GitHub Actions: `https://github.com/[org]/robo-trader/actions`
- Specific workflow: Click on workflow name

### Notifications
- Email: Automatic for failures
- Slack: Configure webhook (optional)
- Discord: Configure webhook (optional)

## Troubleshooting

### Workflow Fails on Dependencies

**Python:**
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Test locally
pip install -r requirements.txt
pytest
```

**Frontend:**
```bash
# Update package-lock.json
cd ui && npm ci

# Test locally
npm run lint
npm run test
```

### Docker Build Fails

```bash
# Test locally
docker build -t robo-trader:test .
docker run --rm robo-trader:test

# Check cache
docker builder prune
```

### Integration Tests Fail

```bash
# Check services
docker-compose up -d postgres redis

# Test database connection
curl -f http://localhost:8000/api/health

# Check logs
docker-compose logs -f
```

## Migration from Old Workflow

The old `quality-checks.yml` has been deprecated. See [WORKFLOWS.md](../WORKFLOWS.md) for migration guide.

**New advantages:**
- 5x more validations
- Better security scanning
- Faster execution (parallel jobs)
- Better caching
- Comprehensive documentation

## Contributing

When modifying workflows:

1. Test changes on a feature branch
2. Validate YAML syntax locally
3. Update documentation in [WORKFLOWS.md](../WORKFLOWS.md)
4. Create PR with workflow changes
5. Monitor first run carefully
6. Update branch protection rules if needed

## Resources

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [act - Local GitHub Actions](https://github.com/nektos/act)
- [yamllint](https://github.com/adrienverge/yamllint)

---

**Last Updated:** 2025-11-05
**Maintained By:** DevOps Team
