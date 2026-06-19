"""Dev-only: render Murmur UI states to PNGs so we can refine the design.

Not shipped with the app. Requires playwright + chromium:
    pip install playwright && python -m playwright install chromium
Usage:
    python tools/render_ui.py [out_dir]
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = (ROOT / "murmur" / "ui" / "main" / "index.html").as_uri()
PILL = (ROOT / "murmur" / "ui" / "pill" / "index.html").as_uri()
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/murmur-shots")
OUT.mkdir(parents=True, exist_ok=True)

VIEWS = ["dictate", "modes", "history", "settings"]


def shot(page, path):
    page.wait_for_timeout(450)  # let entrance animations settle
    page.screenshot(path=str(path))
    print("wrote", path)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---- Main window, dark theme, every view ----
        page = browser.new_page(viewport={"width": 1180, "height": 820}, device_scale_factor=2)
        page.goto(MAIN)
        page.wait_for_timeout(400)
        for v in VIEWS:
            page.click(f'.nav__item[data-view="{v}"]')
            shot(page, OUT / f"main-{v}.png")

        # ---- Light theme (dictate + settings) ----
        page.evaluate("document.documentElement.dataset.theme = 'light'")
        page.click('.nav__item[data-view="dictate"]')
        shot(page, OUT / "main-dictate-light.png")
        page.click('.nav__item[data-view="settings"]')
        shot(page, OUT / "main-settings-light.png")
        page.close()

        # ---- Floating pill, a few states ----
        page2 = browser.new_page(viewport={"width": 520, "height": 200}, device_scale_factor=2)
        page2.goto(PILL)
        for st in ["idle", "listening", "transcribing", "polishing", "done"]:
            page2.evaluate(f"window.pill && window.pill.setState('{st}')")
            page2.wait_for_timeout(350)
            shot(page2, OUT / f"pill-{st}.png")
        page2.close()

        browser.close()


if __name__ == "__main__":
    main()
