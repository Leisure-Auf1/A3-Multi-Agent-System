# Security Policy

## Supported Versions

| Version | Supported |
|:--------|:----------|
| v1.0.0 | ✅ Active support |
| v0.x | ❌ Upgrade to v1.0.0 |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Please report security issues privately via:

- Email: open an issue with "[SECURITY]" prefix and we will exchange contact privately
- GitHub: [Report a security vulnerability](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/security/advisories/new)

We will respond within 7 days with:
1. Confirmation of receipt
2. Assessment of severity
3. Timeline for fix

## Security Architecture

### API Key Storage

A3-Agent uses **OS-level credential stores** for API key encryption:

| Platform | Backend |
|:---------|:--------|
| Windows | Credential Manager (via `keyring`) |
| Linux | Secret Service / D-Bus (via `keyring`) |
| macOS | Keychain (via `keyring`) |
| Headless/Server | Local obfuscation fallback; configure an OS keyring for production |

API keys are not stored as plaintext by the application.

- `llm.json` configuration file contains `keyring://provider` references, not actual keys
- The XOR fallback is obfuscation, not cryptographic protection; anyone who can read both local files can recover the key
- Production deployments must provide a working OS-level keyring and protect the application data directory

### User Data Isolation

| Platform | Path |
|:---------|:-----|
| Windows | `%APPDATA%\A3-Agent\` |
| Linux/macOS | `~/.a3-agent/` |

User data includes:
- `workspace/{user_id}/config/` — per-user API configuration (key references or obfuscated fallback values)
- `storage/` — SQLite learning database
- `logs/` — Application logs

### Authentication

The FastAPI backend supports:
- **Opaque bearer sessions** stored server-side with a 24-hour expiry
- **Guest mode** for single-user desktop usage
- Passwords are hashed with PBKDF2-HMAC-SHA256 before storage
- Administrative access can be bootstrapped with the comma-separated `A3_ADMIN_EMAILS` environment variable

Cross-origin browser access is restricted to local UI origins by default. Set
`A3_CORS_ORIGINS` to a comma-separated allowlist for deployed frontends.

### Dependencies

We monitor dependencies for known vulnerabilities. To check:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

## Best Practices for Users

1. **Always download from official sources**: [GitHub Releases](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)
2. **Verify checksums** after downloading
3. **Use OS-level keyring** for API key storage (default on Windows/Linux desktop)
4. **Don't share your `a3.db` file** — it may contain personal learning data
5. **Keep A3-Agent updated** to the latest release

## Reporting Other Concerns

For non-security issues, please use regular [GitHub Issues](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues).
