# Logging Configuration Guide

## Overview

The Robo Trader system uses structured logging with loguru to provide clear, categorized log messages. Logs are written to both console (for real-time monitoring) and files (for troubleshooting and auditing).

## Log Levels

### DEBUG Level
**Purpose**: Detailed information for debugging and troubleshooting
**When to use**:
- Internal state checks
- Variable dumps
- Step-by-step execution traces
- Detailed API responses
- Internal operations that help with debugging

**Example usage**:
```python
logger.debug(f"OAuth service retrieved: {oauth_service is not None}")
logger.debug(f"Checking API credentials - Key present: {bool(api_key)}")
```

### INFO Level
**Purpose**: General operational events and important milestones
**When to use**:
- Operation starts/completions
- Major milestones
- Normal operation events (OAuth success, portfolio scan completed)
- User actions
- System health updates

**Example usage**:
```python
logger.info("Portfolio scan request initiated")
logger.info("Valid OAuth token found for user: WH6470")
logger.info("Portfolio scan completed successfully: 81 holdings loaded")
```

### WARNING Level
**Purpose**: Important events that don't stop execution but may need attention
**When to use**:
- Non-critical issues
- Fallbacks being used
- Retries
- Missing optional dependencies
- Authentication warnings

**Example usage**:
```python
logger.warning("Failed to initialize broker client with new token")
logger.warning("Portfolio scan completed but no holdings found")
```

### ERROR Level
**Purpose**: Error events that may still allow execution
**When to use**:
- Failures
- Exceptions
- Critical issues
- Operation failures

**Example usage**:
```python
logger.error("Orchestrator not available for portfolio scan")
logger.error(f"Failed to auto-trigger portfolio scan: {e}", exc_info=True)
```

### CRITICAL Level
**Purpose**: System failures that require immediate attention
**When to use**:
- System crashes
- Data corruption
- Unrecoverable errors

**Example usage**:
```python
logger.critical("Database connection failed - shutting down")
```

## Logging Configuration

### Default Configuration

By default, the system runs at **INFO level**, logging:
- INFO and above to **console** (colored output)
- DEBUG and above to **files** (always capture DEBUG in files for troubleshooting)

### Environment Variable Control

You can control the logging level using the `LOG_LEVEL` environment variable:

```bash
# Normal operation (INFO level - default)
python -m src.main --command web

# Enable DEBUG logging for troubleshooting
LOG_LEVEL=DEBUG python -m src.main --command web

# Only show warnings and errors
LOG_LEVEL=WARNING python -m src.main --command web
```

### Log Files

Logs are written to the `logs/` directory:

- **backend.log** - All logs at DEBUG level (detailed for troubleshooting)
- **errors.log** - WARNING, ERROR, and CRITICAL only
- **critical.log** - ERROR and CRITICAL only
- **frontend.log** - Frontend-specific logs

Each file is:
- Automatically rotated when it reaches 10MB (backend) or 5MB (errors)
- Compressed with gzip
- Retained for 7-90 days depending on file type

## Coordinator Logging

All coordinators inherit from `BaseCoordinator` and have access to logging methods:

```python
# Use DEBUG for internal operations
self._log_debug(f"Initializing with config: {config}")

# Use INFO for important milestones
self._log_info("Coordinator initialized successfully")

# Use WARNING for non-critical issues
self._log_warning("Feature not available, using fallback")

# Use ERROR for failures
self._log_error(f"Failed to process: {error}", exc_info=True)
```

## Best Practices

### ✅ DO
- Use DEBUG for internal state checks and variable values
- Use INFO for user actions and major milestones
- Use WARNING for expected failures and fallbacks
- Use ERROR for unexpected failures
- Include context in log messages (user ID, operation, etc.)
- Use `exc_info=True` when logging exceptions

### ❌ DON'T
- Log sensitive information (passwords, API keys, tokens)
- Use INFO for every variable or step
- Log at DEBUG level in production (unless troubleshooting)
- Use print() statements instead of logger
- Suppress exceptions without logging

## Example: Portfolio Scan Logging

### Before (Too Verbose)
```python
logger.info("=" * 80)
logger.info("PORTFOLIO SCAN REQUEST - Starting")
logger.info("=" * 80)
logger.info(f"OAuth service retrieved: {oauth_service is not None}")
logger.info(f"Stored token check: {token_data is not None}")
logger.info("Proceeding with normal portfolio scan")
logger.info("Executing portfolio scan")
logger.info(f"Portfolio scan result: {result}")
```

### After (Properly Categorized)
```python
# INFO - Important milestone
logger.info("Portfolio scan request initiated")

# DEBUG - Internal state check
logger.debug(f"Token data retrieved: {token_data is not None}")

# INFO - Major milestone
logger.info("Executing portfolio scan")

# INFO - Operation completion
logger.info("Portfolio scan completed successfully: 81 holdings loaded")
```

## Enabling Debug Logging

When you need detailed troubleshooting:

```bash
# Enable DEBUG logging
export LOG_LEVEL=DEBUG
python -m src.main --command web

# Or inline
LOG_LEVEL=DEBUG python -m src.main --command web
```

Then check the logs:
```bash
# View all logs (includes DEBUG)
tail -f logs/backend.log

# View only INFO and above
tail -f logs/backend.log | grep -E "INFO|WARNING|ERROR|CRITICAL"
```

## Filtering Logs

You can filter logs by level when viewing:

```bash
# View only errors and critical
grep "ERROR\|CRITICAL" logs/backend.log

# View specific component
grep "PortfolioCoordinator" logs/backend.log

# View recent errors
tail -100 logs/errors.log
```

## Performance Considerations

- **Console output** is filtered to your configured level (default: INFO)
- **File output** always captures DEBUG level (for troubleshooting)
- This provides both clean console output and detailed file logs
- Log rotation prevents disk space issues

## Troubleshooting

### Issue: Too many logs in console
**Solution**: Running at INFO level by default. If you need even fewer logs, set:
```bash
LOG_LEVEL=WARNING python -m src.main --command web
```

### Issue: Need more detail
**Solution**: Enable DEBUG level:
```bash
LOG_LEVEL=DEBUG python -m src.main --command web
```

### Issue: Logs not appearing
**Check**:
1. Log level setting: `echo $LOG_LEVEL`
2. Backend running: `curl http://localhost:8000/api/health`
3. Log files created: `ls -la logs/`

### Issue: Can't find specific log
**Check**:
1. DEBUG logs in `logs/backend.log` (all levels captured)
2. Use grep to filter: `grep "portfolio" logs/backend.log`
3. Check error logs: `tail logs/errors.log`

## Summary

- **Default**: INFO level (clean console, detailed file logs)
- **Control**: `LOG_LEVEL` environment variable
- **Files**: Always capture DEBUG for troubleshooting
- **Console**: Filtered to configured level
- **Best Practice**: Use DEBUG for internal, INFO for milestones, WARNING/ERROR for issues
