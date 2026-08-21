# Security Policy

## Reporting a vulnerability

Report privately through GitHub's [Security Advisories](https://github.com/HibikiHata/almanac-calendar/security/advisories/new).
Please do not open a public issue for a security problem.

You will get an acknowledgment within 7 days.

After triage I will confirm or decline the report, develop a fix privately,
and publish a security advisory crediting you (unless you prefer otherwise)
once a fixed release is out. This is a solo-maintained project; complex fixes
may take a few weeks.

## Supported versions

Only the latest release (and the moving `v1` tag that follows it) is
supported. Fixes are not backported.

## What this project touches

Knowing the boundaries is usually enough to judge whether something is a
security problem here.

- **Network.** The Action and the library run entirely offline: calendars are
  computed from astronomical tables bundled with the package. The only code
  that touches the network is the development-time verification tooling under
  `src/almanac_calendar/_generate/`, which the Action never executes.
- **Tokens and secrets.** The library reads none. The scheduled `generate`
  workflow uses the repository's own `GITHUB_TOKEN` solely to push the
  rendered SVGs to the `output` branch.
- **Dependencies.** The runtime uses the Python standard library only. The
  test suite additionally needs `pytest`.
- **Third-party Actions.** Every `uses:` in this repository is pinned to a
  full commit SHA.

## Out of scope

- Vulnerabilities in GitHub Actions itself or in the third-party actions this
  repository pins — report those upstream.
- A dependency version with a known CVE, unless the vulnerable code is
  actually reachable from this project.
- Anything that requires write access to this repository or a compromised
  workflow token.

If you used AI tools to find or write up the issue, say so, and verify the
proof of concept reproduces before reporting. Unverified machine-generated
reports are closed without response.
