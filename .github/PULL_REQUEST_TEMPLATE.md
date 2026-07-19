## Description

Please include a summary of the change and which issue is fixed. Include relevant motivation and context.

Fixes # (issue number)

## Type of Change

- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Release/packaging

## How Has This Been Tested?

Please describe the tests that you ran to verify your changes.

- [ ] `make test` — all 1154 tests pass
- [ ] Manual E2E test on [platform]
- [ ] Release validation: `python scripts/release_check.py`

## Architecture Constraints

> ⚠️ **DO NOT modify**: `src/agents/`, `src/workflow/`, Veritas-Core

- [ ] I confirm no changes to `src/agents/`
- [ ] I confirm no changes to `src/workflow/`
- [ ] I confirm no changes to Veritas-Core
- [ ] I confirm `make test` passes locally

## Checklist

- [ ] My code follows the project's code style
- [ ] I have updated the documentation accordingly
- [ ] I have added tests that prove my fix/feature works
- [ ] All new and existing tests pass
