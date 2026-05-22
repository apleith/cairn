# Privacy

Cairn is built to be **local-first**. It is designed to run on your own
hardware, store your data on your own hardware, and never send your health
data to any third party that you have not explicitly configured.

This document describes what Cairn does and does not do with data.

## What Cairn stores locally

When you run Cairn on your own machine, it writes:

- A SQLite database (`data.db` by default) in the Cairn working directory.
  This database holds your submissions: weight, blood pressure, scale
  responses, food log entries, wearable data imports, and any other field
  the app accepts.
- Plain-text markdown files at paths you configure in `config.yaml`
  (`storage.health_log_path`, `storage.mental_health_log_path`,
  `activities.path`, optionally a food-log path). These files contain
  human-readable copies of the same entries.
- Application logs (where Python and Flask write to stdout / stderr).

**All of this content stays on your machine.** None of it is uploaded to any
Cairn-controlled service, because there is no Cairn-controlled service.

## What Cairn never collects

Cairn does **not** include any of the following:

- Telemetry, usage analytics, or crash reporting that calls home.
- A licensing server, activation server, or "phone-home" check.
- A user account system.
- A marketing pixel, advertising SDK, or third-party tracker.
- An "anonymous" data-sharing toggle that ships data out by default.

If you find a network call in Cairn's source that you cannot account for
from your own configuration, please report it. See [SECURITY.md](SECURITY.md).

## What Cairn can talk to over the network, only if you configure it

Cairn supports a small number of optional outbound integrations. Each one
is **disabled by default**. You opt in by editing `config.yaml`.

| Integration | What it does | When it talks |
|---|---|---|
| ntfy push | Sends notifications to a topic you choose on a server you choose (default `ntfy.sh` or a self-hosted instance) | Only when the scheduler decides to fire a prompt |
| Google Calendar (OAuth) | Reads your own calendar to gate notifications during meetings | Only when the calendar gate runs (every scheduler tick) |
| Outlook (COM) | Reads your local Outlook client | Only when the calendar gate runs |
| Health Connect (Android companion) | Receives wearable data your phone exports | Only when the companion app posts to `/wearable/bulk` |
| Tailscale (recommended) | Lets you reach your own running Cairn from your phone over your own private mesh | Continuously, by design — this is how the phone reaches the app |

If you configure none of these, Cairn runs entirely offline.

## Who can see your data

By default, the Flask server binds to `0.0.0.0` on port 5151. **This means
anything on the same network as your machine can reach Cairn at
`http://<your-machine>:5151/`.** Cairn does not have a username/password
login. Cairn's recommended deployment model is:

1. Run the machine on a network you trust.
2. Use **Tailscale** (or another zero-trust mesh) to give yourself
   phone-to-PC reachability without exposing the port to the LAN or the
   internet.
3. Do **not** port-forward 5151 to the internet. Cairn is not designed for
   that exposure model.

If you do not run Tailscale, you must accept that anyone on your LAN can
reach Cairn. That is a configuration choice the operator owns.

## What HIPAA, GDPR, and similar frameworks have to say

Cairn is not a covered entity, business associate, or data controller under
HIPAA, GDPR, the UK GDPR, or comparable frameworks. The author distributes
Cairn as open-source software. **You** run it. **You** decide what data goes
in. **You** are the data controller for your own copy.

If you intend to use Cairn (or a fork of Cairn) to process anyone else's
health data, you are taking on responsibilities that this software does not
prepare you for, and you should consult counsel before doing so.

## Data export and deletion

Because Cairn stores everything in your local SQLite database and markdown
files, exporting your data means copying those files. Deleting your data
means deleting those files. Cairn does not have a separate "delete account"
flow because there is no account.

## Children

Cairn is intended for adults. Do not run Cairn for or about a minor without
the consent of a parent or guardian and the supervision of that minor's
qualified healthcare provider.

## Changes to this document

This is the privacy posture for Cairn v0.1.0. If a future release changes
this posture, the change will be reflected in the same file and noted in
[CHANGELOG.md](CHANGELOG.md).
