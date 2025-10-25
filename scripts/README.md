# Robo Trader Build & Restart Scripts

> **Critical**: These scripts prevent Docker build cache issues that caused stale code in containers.

## Quick Start

**Most common scenario** - after modifying code:

```bash
# Option 1: Complete restart (recommended)
./restart_server.sh

# Option 2: Just rebuild one service
./scripts/safe-build.sh paper-trading force

# Option 3: Safe restart with optional rebuild
./scripts/restart-safe.sh paper-trading --rebuild
```

## Available Scripts

### 1. `restart_server.sh` ⭐ (Main Script)

**When to use**: Starting/restarting everything after code changes

**What it does**:
- ✅ Stops all services
- ✅ **Rebuilds all containers with NO cache** (prevents stale code!)
- ✅ Starts backend services
- ✅ Starts frontend (React/Vite)
- ✅ Shows unified log stream

**Usage**:
```bash
./restart_server.sh

# Ctrl+C to stop all services
```

**Features**:
- Automatic cache prevention with `DOCKER_BUILDKIT=0`
- Health checks for API gateway
- Beautiful colored output
- Unified log stream (backend + frontend)
- Environment variable loading from `.env`

**Exit codes**:
- `0` - Success
- `1` - Docker build failed or frontend failed to start

---

### 2. `scripts/safe-build.sh`

**When to use**: Building a single service after code changes

**Usage**:
```bash
# Build with cache (faster, may use stale code)
./scripts/safe-build.sh paper-trading

# Build without cache (slower, guaranteed fresh)
./scripts/safe-build.sh paper-trading force

# Build all services
./scripts/safe-build.sh all force
```

**What it does**:
- ✅ Disables BuildKit cache management
- ✅ Optionally forces clean rebuild
- ✅ Automatically verifies build integrity
- ✅ Suggests fixes if cache is stale

**Verification output**:
- ✅ If routes are correct (for paper-trading)
- ✅ If service URLs use container names (for api-gateway)
- ❌ Warns if stale cache detected

---

### 3. `scripts/restart-safe.sh`

**When to use**: Restarting services with optional rebuild

**Usage**:
```bash
# Restart specific service (no rebuild)
./scripts/restart-safe.sh paper-trading

# Restart specific service with rebuild
./scripts/restart-safe.sh paper-trading --rebuild

# Restart all services
./scripts/restart-safe.sh all

# Restart all with rebuild
./scripts/restart-safe.sh all --force
```

**What it does**:
- ✅ Optionally removes old images
- ✅ Rebuilds with `DOCKER_BUILDKIT=0`
- ✅ Starts services in order
- ✅ Waits for health checks
- ✅ Verifies no stale cache

**Output**:
- Docker container status
- Cache verification results
- Next steps for testing

---

### 4. `scripts/rebuild-all.sh` 🔥

**When to use**: Everything is broken, need fresh start

**Usage**:
```bash
./scripts/rebuild-all.sh

# Will ask for confirmation before proceeding
```

**What it does**:
- ✅ Stops all containers
- ✅ **Removes ALL robo-trader images**
- ✅ Removes dangling layers
- ✅ Rebuilds everything without cache
- ✅ Starts all services

**⚠️ Warning**: This is aggressive and will take time. Use only when:
- Stale cache won't go away
- Containers behave unpredictably
- Nothing else works
- You suspect deep Docker state corruption

**Time**: Usually 5-10 minutes depending on internet speed

---

### 5. `scripts/verify-cache.sh`

**When to use**: Checking if containers have stale code

**Usage**:
```bash
# Check all services
./scripts/verify-cache.sh all

# Check single service
./scripts/verify-cache.sh paper-trading

# After rebuilding any service
./scripts/verify-cache.sh
```

**What it does**:
- ✅ Compares local file hashes with container hashes
- ✅ Checks for stale code signatures
- ✅ Returns exit code 0 (OK) or 1 (STALE)

**Output**:
```
🔍 Cache Verification Script

Checking paper-trading...
  ✅ Hashes match: a1b2c3d4e5f6...

Checking api-gateway...
  ✅ using container names
```

**Exit codes**:
- `0` - All services have fresh code
- `1` - Some services have stale cache (rebuild with scripts/safe-build.sh)

---

## Common Scenarios

### Scenario 1: Modified code, want to restart

```bash
./restart_server.sh
```

Builds with fresh code, starts everything.

### Scenario 2: Modified paper-trading service only

```bash
./scripts/safe-build.sh paper-trading force
docker-compose up -d paper-trading
```

Quick rebuild of just one service.

### Scenario 3: Suspicious stale cache

```bash
# Check first
./scripts/verify-cache.sh all

# If stale, rebuild
./scripts/safe-build.sh paper-trading force
```

Verifies cache before deciding to rebuild.

### Scenario 4: Complete reset needed

```bash
./scripts/rebuild-all.sh
```

Nuclear option - removes everything and rebuilds.

### Scenario 5: Restart without rebuilding

```bash
./scripts/restart-safe.sh all
```

Just restarts containers, no rebuild (faster if you trust the images).

---

## Troubleshooting

### Script won't run: `Permission denied`

```bash
chmod +x scripts/*.sh
chmod +x restart_server.sh
```

### Container still has old code after rebuild

```bash
# Verify cache is fresh
./scripts/verify-cache.sh paper-trading

# If stale, force rebuild
./scripts/safe-build.sh paper-trading force
```

### Build takes forever

Normal! First build caches everything. Subsequent builds should be faster.

```bash
# If really stuck, use aggressive rebuild
./scripts/rebuild-all.sh
```

### Docker Compose not found

Make sure you have Docker Compose installed:

```bash
docker-compose version
```

### Port already in use

Kill the process using the port:

```bash
# Port 3000 (frontend)
lsof -ti:3000 | xargs kill -9

# Port 8000 (API gateway)
lsof -ti:8000 | xargs kill -9
```

---

## Environment Variables

Scripts respect `.env` file if present:

```bash
# .env
DB_PASSWORD=secure_password
RABBITMQ_PASSWORD=secure_password
BROKER_API_KEY=your_key
```

Loaded automatically by `restart_server.sh`

---

## How These Scripts Prevent Cache Issues

### The Problem
Docker BuildKit caches intermediate layers. If source files change but timestamps don't, Docker thinks nothing changed and reuses cached layer with old code.

### The Solution
All scripts use `DOCKER_BUILDKIT=0` which:
- Disables BuildKit's aggressive caching
- Uses simpler, more predictable builder
- Ensures code changes are detected

### The Verification
Scripts automatically verify:
- File hashes match between local and container
- Routes have correct format
- Service URLs use container names

---

## Advanced Usage

### Run build with specific arguments

```bash
# Custom build argument
DOCKER_BUILDKIT=0 docker-compose build --build-arg CACHE_BUST=$(date +%s)
```

### Monitor logs during build

```bash
# In separate terminal
docker-compose logs -f
```

### Debug a service

```bash
# Enter container shell
docker exec -it robo-trader-paper-trading bash

# Check code
cat /app/main.py

# Compare hash
md5sum /app/main.py
```

### Disable BuildKit globally

```bash
# Add to ~/.bashrc or ~/.zshrc
export DOCKER_BUILDKIT=0
```

---

## Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

CHANGED=$(git diff --name-only | grep "^services/" | head -1)
if [ -n "$CHANGED" ]; then
    echo "⚠️  Service code changed. Remember to rebuild:"
    echo "   ./scripts/safe-build.sh <service> force"
    echo "   OR: ./restart_server.sh"
fi
```

Then:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Performance Tips

1. **First build is slow** - Docker downloads bases, installs deps, caches layers
2. **Subsequent builds are fast** - Uses cache (unless you disable it)
3. **Use `--rebuild` sparingly** - Only when you suspect stale cache
4. **Check `verify-cache.sh` first** - Before rebuilding everything

---

## Support

For detailed information see:
- `@documentation/BUILD_CACHE_PREVENTION.md` - Cache prevention guide
- `@documentation/CONTAINER_NETWORKING.md` - Networking setup
- CLAUDE.md - Project rules and patterns
