# Robo Trader - Suggested Commands

## Development

### Backend
```bash
# Start backend server
python -m src.main --command web

# Check health
curl -m 3 http://localhost:8000/api/health

# Run tests
pytest

# Run specific test
pytest tests/test_morning_trading_session.py

# Run tests with coverage
pytest --cov

# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### Frontend
```bash
cd ui

# Start dev server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Preview production build
npm run preview
```

## Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

## System Commands (Darwin/macOS)

### Port Management
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Find what's using a port
lsof -i:8000
```

### File Operations
```bash
# List files
ls -la

# Find files
find . -name "*.py"

# Search in files
grep -r "pattern" .

# Search in Python files only
grep -r "pattern" --include="*.py"
```

### Process Management
```bash
# List Python processes
ps aux | grep python

# Kill process by name
pkill -f "python -m src.main"

# Kill process by PID
kill -9 <PID>
```

## Pre-Deploy Checklist
1. Backend health: `curl -m 3 http://localhost:8000/api/health` → 200
2. Frontend health: `curl -m 3 http://localhost:3000` → 200
3. Tests pass: `pytest`
4. No ERROR/exceptions in logs
5. Restart backend after code changes
