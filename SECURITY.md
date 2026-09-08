# Security Policy

The Kairo engineering team takes the security and safety of our autonomous assistant platform seriously.

---

## Supported Versions

Only the latest stable release receives active security updates and vulnerability patches:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability in Kairo, please report it via **GitHub Private Vulnerability Reporting** or submit an encrypted report to our designated security triage channel.

**Please DO NOT open public issues, discussions, or pull requests for suspected security vulnerabilities.**

### What to Include
When submitting a report, please include:
- A clear description of the vulnerability, potential impact, and attack vector.
- Step-by-step reproduction instructions or a safe proof-of-concept.
- Any relevant logs, stack traces, or configuration contexts (with private keys redacted).
- Proposed mitigations or patches if available.

---

## Responsible Disclosure & Response Timeline

1. **Initial Acknowledgment**: Within 24 hours of receiving a vulnerability report.
2. **Assessment & Triage**: Within 72 hours to confirm severity and exploitability.
3. **Remediation & Patch**: A fix will be developed, tested against our automated test matrix, and deployed to staging.
4. **Public Disclosure**: Coordinated disclosure will occur only after an official patch and advisory are published.

---

## Secrets Handling Policy

- Kairo strictly forbids hardcoded credentials, API keys, or JWT secrets in code or commits.
- All secrets must be injected at runtime via environment variables or cloud secret managers.
- Continuous CI security scanners inspect every commit for accidental credential leakage.
- `MemorySanitizer` scrubs secrets from user conversations before persistence in long-term memory.

---

## Emergency Response & Incident Protocol

In the event of active exploitation, security escalation, or unauthorized actions:
1. **Emergency Stop**: Administrators and users can trigger the global or user-scoped Emergency Stop via `POST /api/v1/security/emergency-stop`.
2. **Revocation**: Rotate master API keys (`OPENROUTER_API_KEY`, `JWT_SECRET_KEY`, database credentials).
3. **Audit Inspection**: Review the immutable audit log (`GET /api/v1/security/audit`) to trace all executed and attempted actions.
4. Detailed incident recovery procedures are documented in [docs/incident-response.md](docs/incident-response.md).
