# Security Policy

## Reporting a vulnerability

Report privately through GitHub's [Security Advisories](https://github.com/HibikiHata/almanac-calendar/security/advisories/new).
Please do not open a public issue for a security problem.

Expect an initial response within a week.

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
