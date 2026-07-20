# Release Checklist

> For maintainers preparing an A3 release.

---

## Pre-Release

- [ ] All tests pass: `make test` (2640 tests, 0 failures)
- [ ] Security audit passes (v1 routes auth-protected)
- [ ] Persistence audit passes (user lifecycle verified)
- [ ] UI audit passes (all 6 tabs functional)
- [ ] README updated (version, test count, badges)
- [ ] Changelog updated with this version's changes
- [ ] Documentation reviewed (links valid, no stale content)

---

## Build

### Windows

```powershell
cd desktop
build.bat
# Output: dist/A3-Agent-v7.1.1-win64.zip
```

Verify:
- [ ] `.exe` launches without errors
- [ ] Browser opens automatically
- [ ] Demo mode works (no API key)
- [ ] Settings → LLM configuration works

### Linux

```bash
pyinstaller A3-Agent.spec
# Output: dist/A3-Agent-linux-x64.tar.gz
```

Verify:
- [ ] Binary launches without errors
- [ ] Workspace created at `~/.a3-agent/`

### Docker

```bash
docker build -t leisureauf1/a3-multi-agent-system:latest .
docker run -p 8501:8501 -p 8000:8000 leisureauf1/a3-multi-agent-system:latest
```

Verify:
- [ ] HTTP 200 on `http://localhost:8501`
- [ ] HTTP 200 on `http://localhost:8000/health`

---

## Security

- [ ] Register/login/logout flow works
- [ ] Auth gate blocks unauthenticated access
- [ ] Token expiry (24h) enforced
- [ ] Role-based permissions correct
- [ ] Token budget enforcement works
- [ ] v1 routes have auth protection
- [ ] No secrets in repository
- [ ] Audit log writes to disk

---

## Documentation

- [ ] README.md — product intro, quick start, architecture
- [ ] docs/user/getting-started.md — 5-minute tutorial
- [ ] docs/user/installation.md — Windows/Linux/Docker
- [ ] docs/user/faq.md — common questions
- [ ] docs/developer/architecture.md — system design
- [ ] docs/developer/api.md — REST API reference
- [ ] docs/release/changelog.md — version history
- [ ] docs/demo/demo-script.md — demo walkthrough

---

## GitHub Release

- [ ] Tag: `v7.1.1`
- [ ] Release title: "A3-Agent v7.1.1"
- [ ] Attach: Windows `.zip`, Linux `.tar.gz`
- [ ] Release notes from changelog
- [ ] Badges updated in README

---

## Post-Release

- [ ] CI pipeline passes on tag push
- [ ] Docker image published
- [ ] Streamlit Cloud demo updated
- [ ] Notify users (if applicable)
