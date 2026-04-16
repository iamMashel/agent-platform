# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately via
[GitHub Security Advisories](https://github.com/mashelodera/agent-platform/security/advisories/new).

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

You will receive a response within 5 business days.

## Security practices in this project

- **No secrets in the repository.** All secrets go in `.env` (git-ignored). Use `.env.example` for templates.
- **GitHub Actions pins actions to full commit SHAs**, not floating tags, to reduce supply-chain risk.
- **Non-root Docker containers.** The production container runs as the `app` user.
- **CORS is permissive by default for local dev.** Lock `allow_origins` to your actual domain in production.
- **Langfuse keys are optional** — the platform degrades gracefully without them.
- **Input validation** is enforced by Pydantic on all API request bodies.
