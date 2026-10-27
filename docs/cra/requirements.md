# Requirements and current state

This page lists what the CRA asks of a manufacturer and where Tapir stands today. "Today" means
what can be seen in this repository; processes outside it may already exist.

Status: **done**, **partly**, **open**, **unknown** (not visible in the repository).

## Vulnerability handling

Required by Annex I, Part II, and for reporting by Art. 14. Reporting applies since
11 September 2026.

| Requirement | Status | Notes |
|---|---|---|
| Contact for vulnerability reports, coordinated disclosure policy | **open** | No `SECURITY.md`; GitHub private vulnerability reporting could be enabled |
| Process to assess and fix reported vulnerabilities without delay | **unknown** | |
| Report actively exploited vulnerabilities and severe incidents to the authorities: early warning within 24 hours, notification within 72 hours, final report later (Art. 14) | **open** | Needs a responsible person and access to the EU single reporting platform |
| Inform users about vulnerabilities and fixes | **partly** | Releases with a changelog exist; no security advisories |
| Security updates, separate from feature updates where possible | **partly** | Releases are built from `master`; no security-only releases |
| Software bill of materials (SBOM) for top-level dependencies | **open** | `poetry.lock` and `pnpm-lock.yaml` are a good basis; an SBOM could be generated in CI |
| Regular testing and review of the product's security | **partly** | Tests, Sonar and dependency review on pull requests exist; no security review process |

## Product requirements

Annex I, Part I. Applies from 11 December 2027.

| Requirement | Status | Notes |
|---|---|---|
| No known exploitable vulnerabilities at release | **partly** | Dependency review on pull requests |
| Secure default configuration | **open** | To be reviewed, e.g. debug settings and default credentials in examples |
| Protection against unauthorised access | **partly** | Login and roles through Keycloak |
| Confidentiality and integrity of stored and transmitted data | **open** | To be reviewed |
| Data minimisation | **open** | See [Relation to the GDPR](gdpr.md) |
| Users can securely and permanently delete their data | **open** | See [Relation to the GDPR](gdpr.md), issue #1123 |
| Logging of security-relevant events | **open** | To be reviewed |

## Documentation and information

| Requirement | Status | Notes |
|---|---|---|
| Technical documentation and risk assessment (Annex VII) | **open** | |
| Information for users (Annex II): contact for vulnerabilities, support period, secure use | **open** | |
| Support period, normally at least five years, stated at release | **open** | |
| Conformity assessment and EU declaration of conformity | **open** | Self-assessment is enough for most software; whether Tapir is in a special category is **open** |
