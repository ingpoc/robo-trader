# Git Hooks for Robo Trader

Automated validation hooks to maintain code quality and architectural standards.

## 🚀 Quick Start

### Install Hooks

```bash
cd /path/to/robo-trader
./scripts/install-hooks.sh
```

This installs:
- **Pre-commit hook** - Fast checks before commit (< 30s)
- **Pre-push hook** - Comprehensive checks before push (1-2 min)

### Uninstall Hooks

```bash
rm .git/hooks/pre-commit
rm .git/hooks/pre-push
```

---

## 📋 What Gets Checked

### Pre-Commit Hook (< 30 seconds)

**Phase 1: Architectural Compliance**
- ✅ File size validation
  - Python: ≤ 350 lines
  - TypeScript/React: ≤ 300 lines
  - Coordinators: ≤ 150 lines (focused) or ≤ 200 lines (orchestrators)
- ✅ Method count validation
  - Python classes: ≤ 10 methods (excluding `__init__`, `__str__`, etc.)

**Phase 2: Python Validation**
- ✅ Compilation check (syntax validation)
- ✅ Linting with `ruff` (if installed)
- ✅ Formatting with `black` (if installed)

**Phase 3: TypeScript/React Validation**
- ✅ TypeScript type checking (`tsc --noEmit`)
- ✅ ESLint (if configured)
- ✅ Prettier formatting (if configured)

### Pre-Push Hook (1-2 minutes)

**All pre-commit checks PLUS:**
- ✅ Backend unit tests (`pytest`)
- ✅ Frontend unit tests (`npm test`)
- ✅ Backend/Frontend build verification
- ✅ API health check (if server running)

---

## 🛠 Scripts Reference

### check_file_sizes.py

Validates file sizes against architectural limits.

**Usage:**
```bash
python3 scripts/check_file_sizes.py
```

**Exit codes:**
- `0` - All files within limits
- `1` - One or more files exceed limits

### check_method_counts.py

Validates class method counts.

**Usage:**
```bash
python3 scripts/check_method_counts.py
```

**Exit codes:**
- `0` - All classes within limit
- `1` - One or more classes exceed limit

---

## ⚙️ Configuration

### Customizing Limits

Edit `scripts/check_file_sizes.py`:

```python
LIMITS = {
    "python": 350,           # Change this
    "typescript": 300,       # Or this
}
```

Edit `scripts/check_method_counts.py`:

```python
MAX_METHODS = 10  # Change this
```

---

## 🚫 Skipping Hooks

```bash
git commit --no-verify
git push --no-verify
```

---

**Generated**: 2025-11-05
