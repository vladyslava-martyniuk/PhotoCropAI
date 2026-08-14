import socket
import threading
import time
import webbrowser

import uvicorn

from main import app


HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}"


def is_app_running():
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    sock.settimeout(0.5)

    try:
        return sock.connect_ex(
            (HOST, PORT)
        ) == 0
    finally:
        sock.close()


def open_browser():
    time.sleep(1.5)
    webbrowser.open(APP_URL)


if __name__ == "__main__":
    # PhotoCropAI already running:
    # just open it again in the browser.
    if is_app_running():
        webbrowser.open(APP_URL)
    else:
        browser_thread = threading.Thread(
            target=open_browser,
            daemon=True,
        )

        browser_thread.start()

        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_config=None,
            access_log=False,
        )