"""One-time Google Calendar OAuth consent flow.

Run once: python -m src.oauth_setup

Opens a browser for Google consent, then writes token.json. After that,
calendar_gate.py can check your calendar silently on every scheduler tick.
"""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from .config import ROOT, load

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main() -> None:
    cfg = load()["calendar"]
    credentials_path = ROOT / cfg["oauth_credentials_path"]
    token_path = ROOT / cfg["oauth_token_path"]

    if not credentials_path.exists():
        raise SystemExit(f"credentials.json not found at {credentials_path}")

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", authorization_prompt_message="")

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"[oauth] token cached to {token_path}")
    print("Calendar gating is now live. Scheduler will suppress prompts during meetings.")


if __name__ == "__main__":
    main()
