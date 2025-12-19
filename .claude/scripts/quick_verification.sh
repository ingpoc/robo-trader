#!/bin/bash

# Quick verification script for verifier-agent
# Outputs structured results in JSON format for easy parsing
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo '{'
echo '  "project_health": {'

# Check servers
echo '    "servers": {'
BACKEND_STATUS=$(curl -s -m 3 http://localhost:8000/api/health > /dev/null 2>&1 && echo '"running"' || echo '"stopped"')
FRONTEND_STATUS=$(curl -s -m 3 http://localhost:3000 > /dev/null 2>&1 && echo '"running"' || echo '"stopped"')
echo "      \"backend\": $BACKEND_STATUS,"
echo "      \"frontend\": $FRONTEND_STATUS"
echo '    },'

# Check database
echo '    "database": {'
DB_FILE="$PROJECT_ROOT/state/robo_trader.db"
if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
    TABLES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    echo "      \"status\": \"exists\","
    echo "      \"size\": \"$DB_SIZE\","
    echo "      \"tables\": $TABLES"
else
    echo "      \"status\": \"missing\""
fi
echo '    },'

# Check config files
echo '    "config": {'
CONFIG_MISMATCH=0
[ ! -f "$PROJECT_ROOT/.claude/settings.json" ] && CONFIG_MISMATCH=1
[ ! -f "$PROJECT_ROOT/.mcp.json" ] && CONFIG_MISMATCH=1
echo "      \"status\": $([ $CONFIG_MISMATCH -eq 0 ] && echo '"ok"' || echo '"missing_files"')"
echo '    }'
echo '  },'

# Check for critical issues
echo '  "issues": ['
ISSUES_FOUND=0

# Check for syntax errors
if python3 -m py_compile "$PROJECT_ROOT/src/core/database_state/portfolio_monthly_analysis_state.py" 2>/dev/null; then
    echo -n ''
else
    [ $ISSUES_FOUND -eq 0 ] && echo '' || echo ','
    echo '    {"type": "syntax_error", "file": "portfolio_monthly_analysis_state.py", "message": "Python compilation failed"}'
    ISSUES_FOUND=1
fi

# Check for import errors in test files
if grep -r "from.*PerplexityService" "$PROJECT_ROOT/tests/" > /dev/null 2>&1; then
    [ $ISSUES_FOUND -eq 0 ] && echo '' || echo ','
    echo '    {"type": "import_error", "message": "Tests using wrong import: PerplexityService instead of PerplexityClient"}'
    ISSUES_FOUND=1
fi

# Check for uncommitted changes
cd "$PROJECT_ROOT"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    [ $ISSUES_FOUND -eq 0 ] && echo '' || echo ','
    echo '    {"type": "uncommitted_changes", "message": "Git working directory not clean"}'
    ISSUES_FOUND=1
fi

echo '  ],'

# Progress summary
echo '  "progress": {'
if [ -f "$PROJECT_ROOT/.claude/progress/feature-list.json" ]; then
    TOTAL=$(jq -r '.total_features' "$PROJECT_ROOT/.claude/progress/feature-list.json" 2>/dev/null || echo "0")
    COMPLETED=$(jq -r '.completed' "$PROJECT_ROOT/.claude/progress/feature-list.json" 2>/dev/null || echo "0")
    PENDING=$(jq -r '.pending' "$PROJECT_ROOT/.claude/progress/feature-list.json" 2>/dev/null || echo "0")
    echo "      \"total\": $TOTAL,"
    echo "      \"completed\": $COMPLETED,"
    echo "      \"pending\": $PENDING,"
    echo "      \"percentage\": $(echo "scale=1; $COMPLETED * 100 / $TOTAL" | bc 2>/dev/null || echo "0")"
else
    echo "      \"status\": \"unknown\""
fi
echo '  }'
echo '}'