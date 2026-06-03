from playwright.sync_api import sync_playwright
import json
import requests
from datetime import datetime
import os
import sys

try:
    # Windows consoles often default to cp1251/cp866 and crash on emoji prints.
    # Keep logs running; Telegram messages are unaffected.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "https://minobraz.midural.ru/activity/3060/?id=3060"

def _load_env():
    """
    Best-effort .env loader (no extra dependencies).
    Supports simple KEY=VALUE lines, ignores comments and blanks.
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
    except Exception:
        # If .env can't be read, we'll rely on real env vars.
        pass


_load_env()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

TARGETS = {
    "👩 Марта": "177Г65Б275511В2286Д97",
    "👧 Кира": "177Г65Б344Д8Б44Д0Е9Г8"
}

SCHOOLS = {
    "🏫 Школа 31": {"name": "МАОУ-СОШ № 31", "limit": 300},
    "🏫 Школа 79": {"name": "МАОУ СОШ № 79", "limit": 288},
}

STATE_FILE = "state.json"


# ---------------- STATE ----------------

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "history" not in data:
                data["history"] = {name: [] for name in TARGETS}
            if "baseline" not in data:
                data["baseline"] = {}
            if "school_baseline" not in data:
                data["school_baseline"] = {}
            return data
    except Exception:
        return {
            "history": {name: [] for name in TARGETS},
            "baseline": {},
            "school_baseline": {},
        }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


# ---------------- TELEGRAM ----------------

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing BOT_TOKEN/CHAT_ID. Fill .env or environment variables.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Ignore HTTP(S)_PROXY / ALL_PROXY from the OS (often socks5 without PySocks).
    session = requests.Session()
    session.trust_env = False
    resp = session.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    }, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram HTTP {resp.status_code}: {resp.text}")
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Telegram returned non-JSON: {resp.text}")
    if not data.get("ok", False):
        raise RuntimeError(f"Telegram error: {data}")


# ---------------- DATA ----------------

def update_history(state, current):
    for name in TARGETS:
        if name not in state["history"]:
            state["history"][name] = []

        if name in current:
            prev = state["history"][name][-1] if state["history"][name] else None
            if prev != current[name]:
                state["history"][name].append(current[name])
            state["history"][name] = state["history"][name][-4:]

            if name not in state["baseline"]:
                state["baseline"][name] = current[name]


# ---------------- PARSING ----------------

def get_frame(page):
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)  # КРИТИЧНО

    for f in page.frames:
        if "edu-inform" in f.url:
            return f

    return None


def select_city(frame):
    frame.locator("div.component-select").nth(0).click()
    frame.page.wait_for_timeout(500)

    options = frame.locator("div.component-select-dropdown-content-option")

    for i in range(options.count()):
        if "Екатеринбург" in options.nth(i).inner_text():
            options.nth(i).click()
            return True

    return False


def select_school(frame, school_name):
    frame.locator("div.component-select").nth(1).click()
    frame.page.wait_for_timeout(500)

    options = frame.locator("div.component-select-dropdown-content-option")

    for i in range(options.count()):
        if school_name in options.nth(i).inner_text():
            options.nth(i).click()
            return True

    return False


def parse_table(frame):
    rows = frame.locator("table tr").all()

    result = {}
    positions = []

    for row in rows:
        text = row.inner_text().strip()
        parts = text.split()

        if len(parts) < 2:
            continue

        if not parts[0].isdigit():
            continue

        pos = int(parts[0])
        number = parts[1]

        positions.append(pos)

        for name, target in TARGETS.items():
            if target in number:
                result[name] = pos

    return result, positions


def get_all_data(page):
    frame = get_frame(page)

    if not frame:
        print("❌ iframe не найден")
        return {}, {}

    print("✅ iframe найден")

    # баннер
    try:
        page.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if (b.innerText.includes('Согласен') || b.innerText.includes('Принять')) {
                    b.click();
                }
            });
        """)
    except:
        pass

    frame.page.wait_for_timeout(2000)

    if not select_city(frame):
        print("❌ город не выбран")
        return {}, {}

    frame.page.wait_for_timeout(1000)

    school_results = {}
    main_result = {}

    for label, school in SCHOOLS.items():
        print(f"🏫 {label}")

        if not select_school(frame, school["name"]):
            print("❌ не нашёл школу")
            school_results[label] = "?"
            continue

        frame.page.wait_for_timeout(2000)

        result, positions = parse_table(frame)

        if label == "🏫 Школа 31":
            main_result = result

        school_results[label] = max(positions) if positions else "?"

    return main_result, school_results


# ---------------- MESSAGE ----------------

def format_message(state, school_results):
    lines = []

    lines.append(f"Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for name in TARGETS:
        hist = state["history"].get(name, [])
        if not hist:
            continue

        base = state["baseline"].get(name)
        delta = hist[-1] - base if base is not None else 0
        delta_str = f" ({delta:+})" if base is not None else ""

        chain = " → ".join(map(str, hist))
        lines.append(f"{name}: {chain}{delta_str}")

    lines.append("")
    lines.append("Длина очереди (свободно/подано):")

    for label, value in school_results.items():
        limit = SCHOOLS[label]["limit"]

        base = state["school_baseline"].get(label)

        if base is None and value != "?":
            state["school_baseline"][label] = value
            base = value

        delta = value - base if base is not None and value != "?" else 0
        delta_str = f" ({delta:+})" if base is not None else ""

        lines.append(f"{label}: {limit}/{value}{delta_str}")

    return "\n".join(lines)


# ---------------- MAIN ----------------

def main():
    state = load_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("---- ЗАПУСК ----", datetime.now())

        try:
            current, schools = get_all_data(page)

            if not schools:
                print("❌ нет данных")
                return

            update_history(state, current)

            message = format_message(state, schools)

            print(message)
            print("📤 отправка...")

            send_telegram(message)
            save_state(state)

            print("✅ отправлено")

        except Exception as e:
            print("Ошибка:", e)


if __name__ == "__main__":
    main()