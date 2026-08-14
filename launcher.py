import threading
import time
import webbrowser

import uvicorn

from main import app


def open_browser():
    time.sleep(1.5)

    webbrowser.open(
        "http://127.0.0.1:8000"
    )


if __name__ == "__main__":
    browser_thread = threading.Thread(
        target=open_browser,
        daemon=True,
    )

    browser_thread.start()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )