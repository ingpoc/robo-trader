# Security Rules for Robo Trader Project

## API Keys and Secrets Management

### CRITICAL: Never Hardcode API Keys
- **NEVER** write API keys, secrets, or tokens directly in any source code file
- **NEVER** commit API keys to version control (Git)
- **ONLY** store API keys in `.env` file
- **ONLY** load API keys from environment variables

### File Restrictions
- **FORBIDDEN**: API keys in `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`, `.toml`, `.xml`, `.config` files
- **ALLOWED**: API keys only in `.env` file (which should be in `.gitignore`)

### Environment Variables Only
- All sensitive configuration must be loaded from environment variables
- Use `os.getenv()` or `load_dotenv()` to read from `.env` file
- Never hardcode fallback values for sensitive data

### Git Security
- `.env` files must be in `.gitignore`
- Never commit `.env` files to repository
- Use placeholder `.env.example` files for documentation

### Detection Patterns
- Block commits containing patterns like:
  - `sk-` (OpenAI/Claude API keys)
  - `pplx-` (Perplexity API keys)
  - `pk_` (Stripe/PayPal keys)
  - `AKIA` (AWS access keys)
  - `AIza` (Google API keys)
  - `Bearer ` followed by long alphanumeric strings

### Code Review Requirements
- All code changes must be reviewed for hardcoded secrets
- Automated tools should scan for API key patterns
- Manual review required for any configuration changes

### Examples of What to Avoid
```python
# ❌ WRONG - Never do this
API_KEY = "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"

# ✅ CORRECT - Always do this
import os
API_KEY = os.getenv('ANTHROPIC_API_KEY')
```

### Configuration Files
- JSON config files should only contain non-sensitive configuration
- Sensitive data must be loaded from environment variables at runtime
- Use placeholder values or empty arrays for sensitive fields in config files

### CI/CD Security
- Never expose secrets in CI/CD pipeline logs
- Use secret management systems (GitHub Secrets, AWS Secrets Manager, etc.)
- Rotate API keys regularly
- Monitor for unauthorized API usage

### Incident Response
- Immediately revoke compromised API keys
- Change all related credentials
- Audit access logs for suspicious activity
- Update security rules based on incidents

## Enforcement
- Automated checks will block commits with hardcoded secrets
- Manual code reviews will verify security compliance
- Security violations will result in immediate remediation requirements