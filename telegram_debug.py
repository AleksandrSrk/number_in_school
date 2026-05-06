import os
from pathlib import Path

import requests


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def main() -> int:
    load_env()
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        print("BOT_TOKEN missing (fill .env)")
        return 2

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        r = requests.get(url, timeout=20)
    except Exception as e:
        print("Request failed:", e)
        return 3

    print("HTTP:", r.status_code)
    try:
        obj = r.json()
    except Exception:
        print("Non-JSON response:", r.text[:500])
        return 4

    print("ok:", obj.get("ok"))
    updates = obj.get("result", []) or []
    print("updates:", len(updates))

    seen = set()
    for u in updates[-50:]:
        msg = (
            u.get("message")
            or u.get("channel_post")
            or u.get("edited_message")
            or u.get("edited_channel_post")
        )
        if not msg:
            continue
        chat = msg.get("chat", {}) or {}
        cid = chat.get("id")
        ctype = chat.get("type")
        title = chat.get("title") or (("@"+chat.get("username")) if chat.get("username") else "") or (chat.get("first_name") or "")

        key = (cid, ctype, title)
        if cid is None or key in seen:
            continue
        seen.add(key)
        print(f"chat_id: {cid} | type: {ctype} | title: {title}")

    print("")
    print("Tip: send a message in the target group while the bot is in it,")
    print("then rerun this script so the group appears in updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

