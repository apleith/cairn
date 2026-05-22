# Security

Cairn handles health data that you choose to enter. While the project is
local-first and has no centralized service to attack, the threat model is
still worth taking seriously: a vulnerability in Cairn could let someone
read your private health data off of your own machine.

## Reporting a vulnerability

Please report security vulnerabilities **privately**, not through public
GitHub issues.

- Email: `alex.leith@gmail.com`
- Subject line: `Cairn security report:` followed by a short summary

Please include:

- The version (commit hash) of Cairn you are testing.
- A description of the vulnerability and how to reproduce it.
- The impact, as you understand it.
- A suggested fix, if you have one.

I will acknowledge a report within 7 calendar days. I am an individual
maintainer, not a security team, so please be patient with timelines.

## Scope

In scope:

- The Flask app (`app.py`, all routes).
- The scheduler (`src/scheduler.py`).
- The Health Connect bulk-ingest endpoint (`/wearable/bulk`).
- The configuration loader and any path-handling code.
- Authentication and authorization assumptions for the deployment model.
- Dependencies pinned in `requirements.txt`, if exploitable.

Out of scope:

- "Anyone on the LAN can reach Cairn" — that is the documented deployment
  posture. See [PRIVACY.md](PRIVACY.md). If you port-forward 5151 to the
  public internet, that is an operator configuration issue, not a Cairn
  vulnerability.
- Browser extensions or other software that observes your local browser
  while you use Cairn.
- The mental-health screening instruments themselves (PHQ-9, GAD-7, WHO-5,
  ISI). Those are validated public-domain tools; concerns about their
  clinical use belong with the original publishers.

## Hardening recommendations for operators

Until Cairn implements first-party authentication, the recommended
deployment is:

1. **Tailscale or equivalent.** Reach Cairn only over a zero-trust mesh.
   Do not expose port 5151 to the LAN, your router, or the internet.
2. **Disk encryption.** Run Cairn on a machine with full-disk encryption
   (BitLocker on Windows, FileVault on macOS, LUKS on Linux). The SQLite
   database is your health record; treat it accordingly.
3. **Backups, encrypted.** Back up `data.db`, the markdown logs, and your
   `config.yaml`. If you use a cloud-sync backup, encrypt before upload.
4. **No shared accounts.** Cairn has no concept of multi-user separation.
   One user, one OS account, one Cairn install.

## Known limitations

These are documented limitations, not vulnerabilities. They will be
addressed in later versions but are not under embargo:

- **No authentication on the Flask app.** The deployment model assumes
  network-level isolation (Tailscale, loopback).
- **`credentials.json` and `token.json` are stored unencrypted at rest.**
  These contain Google OAuth client credentials and refresh tokens for
  calendar access. Anyone with read access to the Cairn working directory
  can use them.
- **No CSRF protection on POST routes.** Combined with the no-auth posture
  above, this means a malicious page open in the same browser that has
  Cairn open could potentially submit fake entries. Treat the trust boundary
  as the network.
- **Pre-v0.1 history is rewritten.** This repository was reinitialized
  before its first public push. The pre-public history is preserved
  locally by the author and is not redistributable; do not assume earlier
  commits exist anywhere public.
