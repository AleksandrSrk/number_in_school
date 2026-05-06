from playwright.sync_api import sync_playwright
import time
import random

URL = "https://minobraz.midural.ru/activity/3060/?id=3060"

TARGETS = {
    "Марта": "177Г65Б275511В2286Д97",
    "Кира": "177Г65Б344Д8Б44Д0Е9Г8"
}


def get_positions(page):
    print("Открываю страницу...")
    page.goto(URL)

    # --- ждём iframe ---
    page.wait_for_selector("iframe", timeout=15000)

    frame = None
    for f in page.frames:
        if "edu-inform" in f.url:
            frame = f
            break

    if not frame:
        print("❌ iframe не найден")
        return {}

    print("✅ iframe найден")

    # --- УБИВАЕМ БАННЕРЫ ЧЕРЕЗ JS ---
    print("Удаляю баннеры через JS...")

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

    try:
        frame.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if (b.innerText.includes('Принять')) {
                    b.click();
                }
            });
        """)
    except:
        pass

    frame.wait_for_timeout(2000)

    # --- ЖДЁМ ЭЛЕМЕНТЫ БЕЗ :visible ---
    print("Жду dropdown...")

    # frame.wait_for_selector("div.component-select-title", timeout=20000)

    # els = frame.locator("div.component-select-title")
    # count = els.count()

    # print("Найдено dropdown:", count)

    # if count < 2:
    #     print("❌ dropdown не загрузились")
    #     return {}

    # --- ВЫБОР МУНИЦИПАЛИТЕТА БЕЗ КЛИКА ---
    print("Открываю муниципалитет...")

    frame.locator("div.component-select").nth(0).click(force=True)
    frame.wait_for_timeout(1000)

    options = frame.locator("div.component-select-dropdown-content-option")

    for i in range(options.count()):
        text = options.nth(i).inner_text()
        
        if "Екатеринбург" in text:
            print("Нашел:", text)
            options.nth(i).click(force=True)
            break

    frame.wait_for_timeout(2000)

    # --- ШКОЛА ---
    print("Открываю школы...")

    frame.locator("div.component-select").nth(1).click(force=True)
    frame.wait_for_timeout(1000)

    options = frame.locator("div.component-select-dropdown-content-option")

    for i in range(options.count()):
        text = options.nth(i).inner_text()
        
        if "МАОУ-СОШ № 31" in text:
            print("Нашел школу:", text)
            options.nth(i).click(force=True)
            break

    frame.wait_for_timeout(3000)

    # --- ЧТЕНИЕ ТАБЛИЦЫ ---
    print("Читаю таблицу...")

    rows = frame.locator("table tr").all()

    result = {}

    for row in rows:
        text = row.inner_text()

        for name, number in TARGETS.items():
            if number in text:
                pos = text.split("\t")[0]
                result[name] = pos

    return result


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--start-maximized"]
        )

        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        last = {}

        while True:
            try:
                print("\n--- НОВАЯ ПРОВЕРКА ---")

                current = get_positions(page)

                print("Текущее:", current)

                if current != last:
                    print("🔥 ИЗМЕНЕНИЯ!", current)
                    last = current
                else:
                    print("Без изменений")

            except Exception as e:
                print("Ошибка:", e)

            print("Ждем 10 минут...\n")
            time.sleep(300 + random.randint(-30, 30))


if __name__ == "__main__":
    main()