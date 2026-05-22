# Cairn

A local-first health journal for people who are tracking a lot at once:
blood pressure from a home cuff, weight, food, medications, validated
mental-health screenings, sleep and steps from a wearable, and the messy
day-to-day signal that comes with managing a chronic condition.

Cairn began as a private companion to one person's bariatric surgery
preparation alongside GLP-1 therapy. It is now released openly under the
Apache License 2.0 for anyone in a comparable situation who wants their
record to live on their own hardware.

> [!IMPORTANT]
> **Cairn is not a medical device, and nothing it shows you is medical
> advice.** Please read [NOT_MEDICAL_ADVICE.md](NOT_MEDICAL_ADVICE.md)
> before you install. It is short, blunt, and serious.

## What Cairn does

- **Phone-reachable quick-entry forms.** Log weight, blood pressure, food,
  pills, and notes from your phone home screen in a few taps. Forms render
  as a Progressive Web App you can pin like any other app.
- **Validated mental-health screenings on a cadence.** PHQ-9 (depression),
  GAD-7 (anxiety), WHO-5 (well-being), and ISI (insomnia) are administered
  at intervals you configure, with scoring done locally.
- **Wearable ingest.** A companion Android app (released separately) can
  POST Health Connect data to Cairn's `/wearable/bulk` endpoint over your
  private network. Cairn stores it, deduplicates it, and rolls it up.
- **Push prompts you control.** Optional [ntfy](https://ntfy.sh) integration
  fires reminders for medications, meals, hydration, and weigh-ins. Quiet
  hours and calendar gating suppress prompts during meetings.
- **Dual-write storage.** Everything lands in both a local SQLite database
  (for analysis) and plain-text markdown files (for Obsidian, grep, and
  long-term human-readable archival).

## What Cairn is not

A medical device. A clinician. A diagnostic tool. A weight-loss program.
A telemedicine product. A cloud service. Read
[NOT_MEDICAL_ADVICE.md](NOT_MEDICAL_ADVICE.md) for the full version.

## Architecture, briefly

```
phone (PWA on home screen)
   |
   |  Tailscale (or other private mesh)
   v
Flask app on your PC  ::  port 5151
   |
   +-- SQLite (data.db)
   +-- markdown logs (health-log.md, food-log.md, mental-health-log.md)
   +-- ntfy.sh (optional, outbound only)
   +-- Outlook or Google Calendar (optional, read-only)
```

The Flask app and a Windows scheduler are two long-running processes. The
scheduler runs every 15 minutes; it reads `schedules.yaml`, checks quiet
hours and your calendar, and decides whether to fire a prompt.

## Install (Windows reference setup)

The author runs Cairn on Windows 11. macOS and Linux should work but are
unverified; please file an issue if you hit platform-specific snags.

```powershell
git clone https://github.com/apleith/cairn.git
cd cairn
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy and edit the configuration files:

```powershell
cp config.example.yaml config.yaml
cp busy-blocks.example.yaml busy-blocks.yaml
cp schedules.example.yaml schedules.yaml
```

Open each one and replace the placeholder values with your own (paths to
your markdown logs, your ntfy topic, your medication labels, your
recurring busy blocks).

## Run

Dev mode:

```powershell
python app.py
```

Open `http://localhost:5151`. The scheduler is a separate process:

```powershell
python -m src.scheduler
```

To install the scheduler as a recurring Windows task (every 15 minutes):

```powershell
powershell -ExecutionPolicy Bypass -File setup-scheduler.ps1
```

## Reach Cairn from your phone (recommended setup)

Cairn has no built-in authentication. **Do not expose port 5151 to the
internet.** Use [Tailscale](https://tailscale.com) or an equivalent
zero-trust mesh to give yourself phone-to-PC access without opening any
ports.

1. Install Tailscale on the PC and on your phone, log both into the same
   tailnet.
2. Find your PC's Tailscale hostname: `tailscale status`.
3. Edit `config.yaml`: set `app.public_url` to
   `http://<your-tailscale-hostname>:5151`.
4. Open that URL on your phone and add it to your home screen.

See [SECURITY.md](SECURITY.md) for the deployment threat model.

## Optional integrations

- **Google Calendar.** Create a desktop OAuth client at
  console.cloud.google.com, save it as `credentials.json` in the project
  root. Set `calendar.provider: google` in `config.yaml`.
- **Outlook.** Set `calendar.provider: outlook`. Cairn talks to the local
  Outlook client via COM (Windows only, requires `pywin32`).
- **ntfy push.** Set `ntfy.topic` to a topic you own on `ntfy.sh` or a
  self-hosted instance.

All three are off unless you configure them.

## Validated instruments

`scales/phq9.yaml`, `scales/gad7.yaml`, `scales/who5.yaml`, and
`scales/isi.yaml` encode public-domain screening instruments with their
standard scoring. Cairn does not modify the instruments. A score is not a
diagnosis; see [NOT_MEDICAL_ADVICE.md](NOT_MEDICAL_ADVICE.md).

## File layout

```
app.py                  Flask app and route definitions
config.yaml             Your runtime configuration (gitignored)
config.example.yaml     Template to copy
busy-blocks.yaml        Recurring busy windows (gitignored)
busy-blocks.example.yaml
schedules.yaml          Fixed-time reminders (gitignored)
schedules.example.yaml
scales/                 PHQ-9, GAD-7, WHO-5, ISI YAML definitions
src/
  config.py             YAML loader
  scales.py             Scale loader and scoring
  storage.py            SQLite + markdown dual-write
  notify.py             ntfy POST
  calendar_gate.py      Quiet hours + recurring + Google Calendar
  outlook_gate.py       Outlook COM client
  activities.py         Activity library parser
  scheduler.py          Cron entrypoint (every 15 minutes)
  food_log_writer.py    Food log writer
  wearable_summary.py   Health Connect summarizers
templates/              Jinja templates for the PWA
static/                 CSS, manifest, service worker, icons
tests/                  pytest suite
docs/public/            Public-facing design notes (none yet)
```

## Status

Cairn is **v0.1.0-alpha**. It works for the author's daily use. It is not
yet polished for first-time installation by other people. Specifically,
some paths still hardcode the author's directory layout (see
[CHANGELOG.md](CHANGELOG.md) for the known list); they will be removed in
v0.2. Pull requests welcome, but please open an issue first so we can
discuss scope.

## Contributing

This is a personal project being shared because other people might want
the same tool. There is no contribution agreement, no CLA, and no
maintainer obligation. If you find a bug, file an issue. If you have a
patch, open a PR with a short rationale.

## Security and disclosure

Please report security vulnerabilities privately. See
[SECURITY.md](SECURITY.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Why "Cairn"

A cairn is a stack of stones that marks where the trail goes. Each entry
in this app is a small stone. Stacked up over weeks and months, they show
the path.
