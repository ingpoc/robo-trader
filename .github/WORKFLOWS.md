# GitHub Workflows Documentation

> **Last Updated**: 2025-11-05 | **Status**: Production Ready

This document describes the GitHub Actions workflows implemented for the robo-trader project, including CI/CD pipelines, security scanning, and deployment automation.

## Overview

The workflow suite implements industry best practices for a production-grade AI trading system:

- ✅ **Comprehensive CI/CD**: Multi-stage validation with parallel execution
- ✅ **Security-First**: Automated vulnerability scanning, SAST, and secret detection
- ✅ **Quality Gates**: Code coverage, linting, type checking, and formatting
- ✅ **Automated Testing**: Unit, integration, and E2E tests across Python and TypeScript
- ✅ **Container Security**: Docker image scanning with Trivy
- ✅ **Dependency Management**: Automated updates via Dependabot
- ✅ **Deployment Automation**: Staging and production deployment with rollback

## Workflow Files

### 1. CI/CD Pipeline (`ci.yml`)

**Triggers:**
- Push to `main`, `develop`, or `claude/**` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Jobs:**

#### Code Quality & Linting (Parallel)

**Python Linting (`lint-python`):**
- ✅ Black formatting check
- ✅ isort import sorting check
- ✅ Ruff linting (fast, comprehensive)
- ✅ Mypy type checking
- **Runtime:** ~2-3 minutes

**Frontend Linting (`lint-frontend`):**
- ✅ ESLint validation
- ✅ TypeScript type checking (`tsc --noEmit`)
- **Runtime:** ~2-3 minutes

#### Testing (Parallel)

**Backend Tests (`test-backend`):**
- **Matrix strategy:** Python 3.11, 3.12
- **Services:** PostgreSQL 15, Redis 7
- ✅ Pytest with coverage (70% minimum)
- ✅ Database migration validation
- ✅ Coverage report upload (HTML + XML)
- ✅ Codecov integration (optional)
- **Runtime:** ~5-8 minutes per Python version

**Frontend Tests (`test-frontend`):**
- ✅ Playwright E2E tests
- ✅ Chromium browser testing
- ✅ Production build validation
- ✅ Test report upload on failure
- **Runtime:** ~4-6 minutes

#### Build Validation (Parallel)

**Docker Build (`build-docker`):**
- ✅ Multi-platform build (linux/amd64, linux/arm64)
- ✅ Build cache optimization (GitHub Actions cache)
- ✅ Container startup validation
- ✅ Health check verification
- ✅ Image artifact upload
- **Runtime:** ~8-12 minutes

**Frontend Build (`build-frontend`):**
- ✅ Production bundle generation
- ✅ Bundle size analysis (<10MB warning)
- ✅ Build artifact upload
- **Runtime:** ~3-5 minutes

#### Integration Tests (Sequential)

**Integration Test (`integration-test`):**
- **Depends on:** test-backend, test-frontend, build-docker
- **Services:** PostgreSQL, Redis
- ✅ Full application startup in Docker
- ✅ API health check validation
- ✅ Log collection on failure
- **Runtime:** ~3-4 minutes

#### Status Check (Final)

**CI Status (`ci-status`):**
- ✅ Aggregates all job results
- ✅ Fails if any critical job fails
- ✅ Required status check for branch protection

**Total CI Pipeline Runtime:** ~15-20 minutes (parallel execution)

---

### 2. Security Scanning (`security.yml`)

**Triggers:**
- Push to `main`, `develop`
- Pull requests to `main`, `develop`
- Weekly schedule (Mondays at 9 AM UTC)
- Manual workflow dispatch

**Jobs:**

#### CodeQL Analysis (`codeql-analysis`)
- **Languages:** Python, JavaScript/TypeScript
- ✅ Security vulnerability detection
- ✅ Code quality analysis
- ✅ SARIF results upload to GitHub Security
- **Runtime:** ~10-15 minutes

#### Dependency Scanning (Parallel)

**Python Dependencies (`dependency-scan-python`):**
- ✅ Safety check (vulnerability database)
- ✅ pip-audit (Python package auditing)
- ✅ JSON output for tracking
- **Runtime:** ~2-3 minutes

**Frontend Dependencies (`dependency-scan-frontend`):**
- ✅ npm audit (moderate+ severity)
- ✅ Dependency vulnerability warnings
- **Runtime:** ~2-3 minutes

#### Secret Scanning (`secret-scan`)
- ✅ TruffleHog OSS integration
- ✅ Verified secrets detection
- ✅ Historical commit scanning
- **Runtime:** ~3-5 minutes

#### Container Security (`container-scan`)
- ✅ Trivy vulnerability scanner
- ✅ CRITICAL + HIGH severity detection
- ✅ SARIF upload to GitHub Security
- ✅ Summary table output
- **Runtime:** ~5-8 minutes

#### SAST (`sast-python`)
- ✅ Bandit security linting
- ✅ JSON report generation
- ✅ Security issue highlighting
- **Runtime:** ~2-3 minutes

#### License Compliance (`license-check`)
- ✅ pip-licenses scanning
- ✅ License report generation
- ✅ Compliance documentation
- **Runtime:** ~2-3 minutes

**Total Security Pipeline Runtime:** ~15-20 minutes (parallel execution)

---

### 3. Deployment (`deploy.yml`)

**Triggers:**
- Push to `main` branch
- Version tags (`v*.*.*`)
- Manual workflow dispatch (with environment selection)

**Jobs:**

#### Build and Push (`build-and-push`)
- ✅ GitHub Container Registry (ghcr.io)
- ✅ Multi-platform builds (amd64, arm64)
- ✅ Image metadata extraction
- ✅ Semantic versioning tags
- ✅ SBOM (Software Bill of Materials) generation
- ✅ Build cache optimization
- **Runtime:** ~10-15 minutes

#### Deploy to Staging (`deploy-staging`)
- **Triggers:** Push to `main` or manual dispatch
- **Environment:** `staging`
- ✅ Automated deployment
- ✅ Smoke tests
- ✅ Deployment notification
- **Runtime:** ~3-5 minutes
- **URL:** https://staging.robo-trader.example.com

#### Deploy to Production (`deploy-production`)
- **Triggers:** Version tags or manual dispatch
- **Environment:** `production`
- **Requires:** Successful staging deployment
- ✅ Blue-green deployment strategy
- ✅ Comprehensive health checks
- ✅ Deployment record creation
- **Runtime:** ~5-8 minutes
- **URL:** https://robo-trader.example.com

#### Create Release (`create-release`)
- **Triggers:** Version tags only
- ✅ Automated changelog generation
- ✅ GitHub release creation
- ✅ Deployment metadata tracking
- **Runtime:** ~1-2 minutes

#### Rollback (`rollback`)
- **Triggers:** Manual workflow dispatch
- ✅ Emergency rollback capability
- ✅ Rollback verification
- **Runtime:** ~3-5 minutes

**Total Deployment Pipeline Runtime:** ~20-30 minutes (sequential)

---

## Dependabot Configuration

**File:** `.github/dependabot.yml`

**Update Schedule:** Weekly (Mondays at 9 AM)

**Ecosystems Monitored:**

1. **Python Dependencies (`pip`)**
   - Groups minor/patch updates together
   - Max 10 open PRs
   - Commit prefix: `chore(deps)`

2. **Frontend Dependencies (`npm`)**
   - Separate groups for production vs development dependencies
   - Max 10 open PRs
   - Commit prefix: `chore(deps)`

3. **Docker Base Images**
   - Max 5 open PRs
   - Commit prefix: `chore(docker)`

4. **GitHub Actions**
   - Max 5 open PRs
   - Commit prefix: `chore(ci)`

**Auto-Merge Strategy:**
- Patch updates: Auto-merge after CI passes (optional)
- Minor updates: Review required
- Major updates: Manual review required

---

## PR and Issue Templates

### Pull Request Template

**File:** `.github/pull_request_template.md`

**Sections:**
- Description and type of change
- Related issues
- Changes made
- Testing checklist (backend + frontend)
- Code quality checklist
- Architecture & best practices checklist
- Security & performance considerations
- Deployment notes
- Rollback plan

**Key Validations:**
- ✅ Follows CLAUDE.md architecture guidelines
- ✅ Uses dependency injection (no global state)
- ✅ Event-driven communication
- ✅ Locked database access via ConfigurationState
- ✅ Claude requests via AI_ANALYSIS queue
- ✅ Modularization limits respected (350 lines, 10 methods)

### Issue Templates

**Bug Report** (`.github/ISSUE_TEMPLATE/bug_report.md`):
- Environment details (backend, frontend, deployment)
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs
- Impact severity
- Affected components

**Feature Request** (`.github/ISSUE_TEMPLATE/feature_request.md`):
- Feature description and problem statement
- Proposed solution and alternatives
- Use cases and benefits
- Implementation considerations (backend, frontend, architecture)
- Security and performance considerations
- Acceptance criteria
- Testing requirements

---

## Branch Protection Rules

**Recommended Settings for `main` and `develop`:**

### Required Status Checks
- ✅ `CI Status Check` (ci.yml)
- ✅ `lint-python`
- ✅ `lint-frontend`
- ✅ `test-backend`
- ✅ `test-frontend`
- ✅ `build-docker`
- ✅ `integration-test`
- ✅ `CodeQL Security Analysis` (security.yml)

### Additional Protections
- ✅ Require branches to be up to date before merging
- ✅ Require pull request reviews (minimum 1)
- ✅ Dismiss stale reviews on new commits
- ✅ Require review from code owners
- ✅ Restrict force pushes
- ✅ Restrict deletions
- ✅ Require linear history (optional)

### Auto-Merge Settings
- ✅ Allow auto-merge after all checks pass
- ✅ Automatically delete head branches after merge

---

## Workflow Optimization Tips

### 1. Caching Strategy

**Python Dependencies:**
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'  # Automatic pip cache
```

**Node Dependencies:**
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '18'
    cache: 'npm'
    cache-dependency-path: ui/package-lock.json
```

**Docker Builds:**
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 2. Parallel Execution

Workflows are designed for maximum parallelism:
- Linting jobs run in parallel
- Testing jobs run in parallel (with matrix strategy)
- Build jobs run in parallel
- Integration tests run sequentially after dependencies

### 3. Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This prevents multiple CI runs on rapid commits.

### 4. Artifact Retention

- Coverage reports: 7 days
- Playwright reports: 7 days (on failure only)
- Docker images: 1 day
- Frontend builds: 7 days
- Test logs: 7 days

---

## Secrets and Environment Variables

### Required Secrets

**Container Registry:**
- `GITHUB_TOKEN` (automatic, no setup needed)

**Deployment (Optional):**
- `DEPLOY_KEY` - SSH key for deployment
- `KUBECONFIG` - Kubernetes configuration (if using K8s)
- `AWS_ACCESS_KEY_ID` - AWS credentials (if using AWS)
- `AWS_SECRET_ACCESS_KEY` - AWS credentials (if using AWS)

**External Services (Optional):**
- `CODECOV_TOKEN` - Codecov integration
- `SLACK_WEBHOOK` - Deployment notifications

### Environment Variables

**Staging:**
- `ENVIRONMENT=staging`
- `DATABASE_URL` - Staging database URL
- `REDIS_URL` - Staging Redis URL

**Production:**
- `ENVIRONMENT=production`
- `DATABASE_URL` - Production database URL
- `REDIS_URL` - Production Redis URL

---

## Monitoring and Notifications

### GitHub Actions Dashboard

View workflow runs: `https://github.com/[org]/robo-trader/actions`

### Notifications

**Slack Integration (Optional):**

Add this step to workflows for Slack notifications:

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

**Email Notifications:**

GitHub sends automatic notifications for:
- Workflow failures
- Required review requests
- Deployment status changes

---

## Troubleshooting

### Common Issues

**1. "Port 8000 already in use" in integration tests**

**Cause:** Previous container not cleaned up

**Solution:** Added cleanup step:
```yaml
- name: Cleanup
  if: always()
  run: docker stop robo-trader-app || true
```

**2. Frontend tests fail with "Playwright not installed"**

**Cause:** Missing Playwright browser installation

**Solution:** Added browser installation:
```yaml
- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium
```

**3. Docker build cache misses**

**Cause:** Cache configuration incorrect

**Solution:** Use GitHub Actions cache:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**4. Test coverage below threshold**

**Cause:** New code without tests

**Solution:**
- Add unit tests for new code
- Update coverage threshold if justified
- Check `htmlcov/` artifact for uncovered lines

**5. Security scan false positives**

**Cause:** Known vulnerabilities in dependencies

**Solution:**
- Update dependencies to patched versions
- Add `continue-on-error: true` for known issues (document in PR)
- Create security exceptions file

---

## Performance Benchmarks

### Expected Runtimes

| Workflow | Duration | Trigger | Frequency |
|----------|----------|---------|-----------|
| CI Pipeline (full) | 15-20 min | Every push/PR | High |
| Security Scan (full) | 15-20 min | Weekly + Push | Medium |
| Deploy to Staging | 15-20 min | Push to main | Medium |
| Deploy to Production | 20-30 min | Version tags | Low |

### Optimization Opportunities

1. **Reduce Docker build time:**
   - Multi-stage builds
   - Layer caching
   - Smaller base images

2. **Reduce test time:**
   - Test parallelization
   - Selective test execution
   - Mock external services

3. **Reduce dependency installation:**
   - Cache restoration
   - Dependency lockfiles
   - Minimal installation

---

## Migration from Old Workflow

### Changes from `quality-checks.yml`

**Removed Issues:**
- ❌ YAML syntax error (name at bottom)
- ❌ Wrong directory for npm commands
- ❌ Missing pytest installation
- ❌ Non-existent validator script
- ❌ No dependency caching

**Added Features:**
- ✅ Comprehensive security scanning
- ✅ Docker build validation
- ✅ Integration testing
- ✅ Deployment automation
- ✅ Multi-environment support
- ✅ Artifact preservation
- ✅ Code coverage reporting
- ✅ Type checking
- ✅ Formatting validation
- ✅ Container security scanning
- ✅ Secret scanning
- ✅ License compliance
- ✅ SBOM generation

**Breaking Changes:**
- None - workflows are additive

**Migration Steps:**
1. Review and merge this PR
2. Update branch protection rules
3. Configure required secrets
4. Test workflows on feature branch
5. Delete `quality-checks.yml` after validation

---

## Best Practices

### 1. Workflow Design

- ✅ Use job dependencies (`needs:`) for sequential execution
- ✅ Use matrix strategy for multi-version testing
- ✅ Use concurrency control to prevent duplicate runs
- ✅ Use `continue-on-error` sparingly (document why)
- ✅ Upload artifacts for debugging
- ✅ Add descriptive job names

### 2. Security

- ✅ Never commit secrets to workflows
- ✅ Use GitHub Secrets for sensitive data
- ✅ Limit secret scope to required jobs
- ✅ Use OIDC for cloud deployments (avoid long-lived credentials)
- ✅ Scan dependencies regularly
- ✅ Review Dependabot PRs promptly

### 3. Testing

- ✅ Run tests on multiple Python versions
- ✅ Use real services (PostgreSQL, Redis) in tests
- ✅ Validate migrations in CI
- ✅ Test Docker image startup
- ✅ Run E2E tests on production builds
- ✅ Monitor test runtime (fail slow tests)

### 4. Deployment

- ✅ Deploy to staging before production
- ✅ Run smoke tests after deployment
- ✅ Keep rollback procedures updated
- ✅ Track deployment metadata
- ✅ Generate changelogs automatically
- ✅ Use semantic versioning

---

## Future Enhancements

**Planned:**
- [ ] Performance regression testing
- [ ] Load testing in CI
- [ ] Automated rollback on health check failure
- [ ] Canary deployments
- [ ] Infrastructure as Code validation (Terraform)
- [ ] Cost optimization analysis
- [ ] Accessibility testing (axe-core)
- [ ] Visual regression testing

**Under Consideration:**
- [ ] Multi-region deployment
- [ ] Chaos engineering tests
- [ ] Kubernetes manifest validation
- [ ] Service mesh integration tests

---

## Support

**Questions?**
- Create an issue using the bug report or feature request template
- Check GitHub Actions logs for detailed error messages
- Review this documentation for common issues

**Contributing:**
- Follow the PR template
- Ensure all CI checks pass
- Update documentation for workflow changes
- Add tests for new workflow features

---

**Document Maintainers:** DevOps Team
**Last Review:** 2025-11-05
**Next Review:** 2026-02-05
