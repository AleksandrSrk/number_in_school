from playwright.sync_api import sync_playwright

URL = "https://minobraz.midural.ru/activity/3060/?id=3060"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(URL)

    print("👉 ВОЙДИ ЧЕРЕЗ ГОСУСЛУГИ, потом нажми Enter")
    input()

    context.storage_state(path="state.json")

    print("✅ Сессия сохранена")