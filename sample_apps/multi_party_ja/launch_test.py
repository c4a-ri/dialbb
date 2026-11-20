"""Open a hub and three spoke consoles on Windows (called by test.bat)."""

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def spoke_commands(python, port, all_bots=False, cli=False):
    url = f"http://localhost:{port}"
    commands = [
        (name, [python, "-m", "dialbb.lib.multi_party.dialbb_spoke",
                f"sample_apps/multi_party_ja/config{index}.yml", name, "--hub-url", url])
        for index, name in enumerate(("田中", "鈴木"), 1)
    ]
    if all_bots:
        third = [python, "-m", "dialbb.lib.multi_party.dialbb_spoke",
                 "sample_apps/multi_party_ja/config3.yml", "山田", "--hub-url", url]
    else:
        module = "dialbb.lib.multi_party.user_spoke" if cli else "dialbb.lib.multi_party.user_spoke_gui"
        third = [python, "-m", module, "山田", "--hub-url", url]
    return commands + [("山田", third)]


def open_console(title, command):
    # /s removes the outer quotes while preserving a quoted executable path.
    command_line = subprocess.list2cmdline(command)
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.Popen(f'cmd.exe /d /s /k "title DialBB - {title} & {command_line}"', cwd=ROOT,
                            creationflags=subprocess.CREATE_NEW_CONSOLE, env=env)


def hub_is_listening(port):
    try:
        with socket.create_connection(("localhost", port), timeout=0.2):
            return True
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-bots", action="store_true", help="Run Yamada as a DialBB app too")
    parser.add_argument("--cli", action="store_true", help="Use a console instead of the GUI for the human participant")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("this launcher opens Windows consoles; use the README commands on other platforms")
    if hub_is_listening(args.port):
        parser.error(f"port {args.port} is already in use; choose another --port")
    open_console("hub", [sys.executable, "-m", "dialbb.lib.multi_party.hub", "--port", str(args.port)])
    deadline = time.monotonic() + 15
    while not hub_is_listening(args.port):
        if time.monotonic() >= deadline:
            parser.error("hub did not start; check its console")
        time.sleep(0.1)
    for name, command in spoke_commands(sys.executable, args.port, args.all_bots, args.cli):
        open_console(name, command)
    print("Opened the hub and three spoke consoles.")
    if not args.all_bots:
        if args.cli:
            print("Press Enter in Yamada's console to join.")
        else:
            print("Use Yamada's GUI window: click Join, type in the input field, and click Send or press Ctrl+Enter.")


if __name__ == "__main__":
    main()
