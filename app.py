from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

import cinedub.runtime_hotfix  # v0.2.3 compatibility fixes
from cinedub.server import run_server
from cinedub.utils import find_free_port, launch_app_window


def main() -> int:
    parser = argparse.ArgumentParser(description="CineDub Studio v0.2.3 Real Localization + Online Update")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    app_root = Path(__file__).resolve().parent
    port = args.port or find_free_port(args.host)
    server = run_server(app_root, args.host, port)
    url = f"http://{args.host}:{port}/"
    print(f"CineDub Studio v0.2.3 Real Localization + Online Update\n{url}")
    if not args.no_browser:
        launch_app_window(url)
    stopped = False
    def stop(*_):
        nonlocal stopped
        if stopped: return
        stopped = True
        server.shutdown()
    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"): signal.signal(signal.SIGTERM, stop)
    launched_at = time.time()
    try:
        while not stopped:
            time.sleep(0.5)
            if not args.no_browser:
                state = server.app_state
                now = time.time()
                if state.ui_seen and now - state.last_heartbeat > 600:
                    stop()
                elif not state.ui_seen and now - launched_at > 600:
                    stop()
    except KeyboardInterrupt:
        stop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
