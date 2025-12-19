#!/bin/bash
#
# Install Git Hooks for Robo Trader
#
# This script installs pre-commit and pre-push hooks to enforce
# code quality and architectural standards.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "🔧 Installing Git hooks for Robo Trader..."
echo ""

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not a git repository"
    echo "   Run this script from within the robo-trader project"
    exit 1
fi

# Make hook scripts executable
chmod +x "$SCRIPT_DIR/pre-commit-hook.sh"
chmod +x "$SCRIPT_DIR/pre-push-hook.sh"
chmod +x "$SCRIPT_DIR/check_file_sizes.py"
chmod +x "$SCRIPT_DIR/check_method_counts.py"

echo "✅ Made hook scripts executable"

# Install pre-commit hook
if [ -f "$GIT_HOOKS_DIR/pre-commit" ]; then
    echo "⚠️  Pre-commit hook already exists, backing up..."
    mv "$GIT_HOOKS_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit.backup"
fi

ln -sf "$SCRIPT_DIR/pre-commit-hook.sh" "$GIT_HOOKS_DIR/pre-commit"
echo "✅ Installed pre-commit hook"

# Install pre-push hook
if [ -f "$GIT_HOOKS_DIR/pre-push" ]; then
    echo "⚠️  Pre-push hook already exists, backing up..."
    mv "$GIT_HOOKS_DIR/pre-push" "$GIT_HOOKS_DIR/pre-push.backup"
fi

ln -sf "$SCRIPT_DIR/pre-push-hook.sh" "$GIT_HOOKS_DIR/pre-push"
echo "✅ Installed pre-push hook"

echo ""
echo "🎉 Git hooks installed successfully!"
echo ""
echo "What the hooks do:"
echo "  📋 Pre-commit (< 30s):"
echo "     - Check file sizes (≤350 lines for Python, ≤300 for TS)"
echo "     - Check method counts (≤10 methods per class)"
echo "     - Validate Python compilation"
echo "     - Run linting and formatting checks"
echo "     - TypeScript type checking"
echo ""
echo "  📋 Pre-push (1-2 min):"
echo "     - All pre-commit checks"
echo "     - Run unit tests"
echo "     - Verify builds succeed"
echo "     - API health checks"
echo ""
echo "💡 To skip hooks (not recommended):"
echo "   git commit --no-verify"
echo "   git push --no-verify"
echo ""
