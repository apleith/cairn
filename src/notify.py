from urllib.request import Request, urlopen

from .config import load


def send(title: str, message: str, click_url: str = None, actions: list[dict] = None, tags: str = "", priority: str = None) -> int:
    cfg = load()
    topic = cfg["ntfy"]["topic"]
    headers = {
        "Title": title,
        "Priority": priority or cfg["ntfy"].get("priority", "default"),
    }
    if click_url:
        headers["Click"] = click_url
    if tags:
        headers["Tags"] = tags
    if actions:
        headers["Actions"] = "; ".join(_fmt_action(a) for a in actions)

    req = Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(req) as resp:
        return resp.status


def _fmt_action(action: dict) -> str:
    kind = action.get("type", "view")
    label = action["label"]
    url = action["url"]
    if kind == "view":
        return f"view, {label}, {url}, clear=true"
    if kind == "http":
        return f"http, {label}, {url}, method=POST, clear=true"
    raise ValueError(f"Unknown action type: {kind}")
