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
| Headless/Server | XOR encryption fallback |

**API keys are NEVER stored in plaintext.**

- `llm.json` configuration file contains `keyring://provider` references, not actual keys
- The XOR fallback is local-only and uses a fixed obfuscation key (not cryptographically secure)
- For production deployments, ensure OS-level keyring is available

### User Data Isolation

| Platform | Path |
|:---------|:-----|
| Windows | `%APPDATA%\A3-Agent\` |
| Linux/macOS | `~/.a3-agent/` |

User data includes:
- `config/` — LLM provider configuration (key references only)
- `storage/` — SQLite learning database
- `logs/` — Application logs

### Authentication

The FastAPI backend supports:
- **JWT authentication** for multi-user deployments
- **Guest mode** for single-user desktop usage
- Passwords are hashed (bcrypt) before storage

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
