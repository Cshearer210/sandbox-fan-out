# Security Policy

## Supported versions

`sandbox-fan-out` is pre-1.0. Security fixes are applied to the latest release on the `main`
branch only.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| < 0.1   | ❌        |

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Report it privately through GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability):

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.
3. Describe the issue, the affected version, and a reproduction if you have one.

You can expect an acknowledgement within a few days. Once a fix is available it will be released
and the advisory published, crediting the reporter unless anonymity is requested.

## Scope notes

`sandbox-fan-out` is a pure standard-library library for splitting work into disjoint slices and
merging per-agent result logs. It is worth being explicit about what it does **not** do, because
the boundary is part of the threat model:

- **Isolation is a file-copy clone, not an OS sandbox.** `checkout()` gives each agent only the
  files its slice needs; it separates *files*, not privileges, processes, or network. It is **not**
  a security boundary. Do not rely on it to contain untrusted code — use a container or a real OS
  sandbox for that.
- **The library runs the work function you give it.** It executes your `work_fn`/`prepare`/
  `teardown` callables as ordinary Python. It performs no `eval`, no `pickle` of untrusted data,
  no network calls, and no shell execution of its own.
- **`merge()` reads JSON lines from a log directory you control.** Point it only at directories
  your own fan-out produced. Malformed lines that are not valid JSON will raise, by design, rather
  than being silently dropped.

There are no bundled credentials, no telemetry, and no third-party runtime dependencies.
