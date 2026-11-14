"""Serve Collect Ricoins locally so it can be installed as an offline web app."""

from __future__ import annotations

import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from game import HOST as API_HOST
from game import PORT as API_PORT
from game import local_service_is_ready, start_server
from terminal import (
    HOST as TERMINAL_HOST,
    PORT as TERMINAL_PORT,
    local_service_is_ready as terminal_service_is_ready,
    start_server as start_terminal_server,
)


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}/"


def main() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    api_server = None if local_service_is_ready() else start_server()
    terminal_server = (
        None if terminal_service_is_ready() else start_terminal_server()
    )
    web_server = None
    try:
        try:
            web_server = ThreadingHTTPServer((HOST, PORT), handler)
        except OSError:
            with urlopen(APP_URL, timeout=3) as response:
                if response.status != 200:
                    raise RuntimeError(f"An app server is already using port {PORT}.")
            print(f"Using the existing game page at {APP_URL}")

        if web_server is not None:
            thread = threading.Thread(
                target=web_server.serve_forever,
                name="ricoins-app",
                daemon=True,
            )
            thread.start()

        print(f"Collect Ricoins is running at {APP_URL}")
        print(f"Game account service is running at http://{API_HOST}:{API_PORT}")
        print(
            f"bix-k0ns0le is running at "
            f"http://{TERMINAL_HOST}:{TERMINAL_PORT}/terminal.html"
        )
        print("Keep this window open while playing. Press Ctrl+C to stop the app.")
        if not webbrowser.open(APP_URL):
            print(f"Open this address in your browser: {APP_URL}")
        if web_server is not None:
            web_server.serve_forever()
        else:
            threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping Collect Ricoins.")
    finally:
        if web_server is not None:
            web_server.shutdown()
            web_server.server_close()
        if api_server is not None:
            api_server.shutdown()
            api_server.server_close()
        if terminal_server is not None:
            terminal_server.shutdown()
            terminal_server.server_close()


if __name__ == "__main__":
    main()
