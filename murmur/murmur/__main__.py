"""Launch Murmur: a main window + a floating pill, driven by the controller."""
from __future__ import annotations

import sys

from . import paths
from .app import Controller, Api

PILL_W, PILL_H = 380, 92


def _fatal_missing_webview() -> None:
    print(
        "Murmur needs pywebview to show its window.\n"
        "Install it with:\n\n    pip install pywebview\n\n"
        "On Windows, also install the WebView2 runtime (most PCs already have it):\n"
        "    https://developer.microsoft.com/microsoft-edge/webview2/\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> None:
    try:
        import webview
    except ImportError:
        _fatal_missing_webview()
        return

    controller = Controller()
    api = Api(controller)

    ui = paths.ui_dir()
    main_url = str(ui / "main" / "index.html")
    pill_url = str(ui / "pill" / "index.html")

    main_window = webview.create_window(
        "Murmur",
        url=main_url,
        js_api=api,
        width=1040, height=720,
        min_size=(880, 600),
        frameless=True,
        easy_drag=False,         # drag via the titlebar's -webkit-app-region instead
        background_color="#0B0B0F",
    )

    pill_window = webview.create_window(
        "Murmur",
        url=pill_url,
        width=PILL_W, height=PILL_H,
        frameless=True,
        on_top=True,
        resizable=False,
        hidden=True,
        transparent=True,        # falls back to the dark color if unsupported
        background_color="#0B0B0F",
    )

    controller.attach_windows(main_window, pill_window)

    def on_start():
        # Park the pill near the bottom-centre of the primary screen.
        try:
            screen = webview.screens[0]
            x = int((screen.width - PILL_W) / 2)
            y = int(screen.height - PILL_H - 80)
            pill_window.move(x, y)
        except Exception:
            pass
        controller.start_services()

    try:
        webview.start(on_start, debug=False)
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
