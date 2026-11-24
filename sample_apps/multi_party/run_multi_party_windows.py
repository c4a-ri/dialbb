"""Run the sample hub in the current console and supervise its spoke consoles."""

import argparse
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def wait_for_hub(hub, hub_url):
    probe_url = f"{hub_url}/socket.io/?EIO=4&transport=polling"
    deadline = time.monotonic() + 15
    while hub.poll() is None and time.monotonic() < deadline:
        try:
            with urlopen(probe_url, timeout=1):
                return hub.poll() is None
        except (TimeoutError, URLError):
            time.sleep(0.2)
    return False


def stop_processes(processes):
    # Give spokes time to finish normally after receiving the hub's last event.
    deadline = time.monotonic() + 2
    for process in processes:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", choices=("ja", "en"))
    parser.add_argument("port", type=int)
    parser.add_argument("max_turns", type=int)
    parser.add_argument("mode", choices=("gui", "cli", "bots"))
    args = parser.parse_args()

    host = "127.0.0.1"
    try:
        with socket.create_connection((host, args.port), timeout=0.5):
            print(f"Port {args.port} is already in use. Choose another --port.", file=sys.stderr)
            return 1
    except OSError:
        pass

    hub_url = f"http://{host}:{args.port}"
    sample = f"sample_apps/multi_party_{args.language}"
    first, second, third = ("田中", "鈴木", "山田") if args.language == "ja" else ("John", "Paul", "Lisa")
    spokes = [
        ["dialbb_spoke", f"{sample}/config1.yml", first],
        ["dialbb_spoke", f"{sample}/config2.yml", second],
    ]
    if args.mode == "bots":
        spokes.append(["dialbb_spoke", f"{sample}/config3.yml", third])
    elif args.mode == "cli":
        spokes.append(["user_spoke", third])
    else:
        spokes.append(["user_spoke_gui", third])

    processes = []
    try:
        hub = subprocess.Popen([sys.executable, "-m", "dialbb.lib.multi_party.hub",
                                "--host", host, "--port", str(args.port), "--max-turns", str(args.max_turns)])
        processes.append(hub)
        if not wait_for_hub(hub, hub_url):
            print("Hub did not start. See the output above.", file=sys.stderr)
            return hub.poll() or 1
        for module, *arguments in spokes:
            processes.append(subprocess.Popen(
                [sys.executable, "-m", f"dialbb.lib.multi_party.{module}", *arguments, "--hub-url", hub_url],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            ))
        return hub.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop_processes(processes)


if __name__ == "__main__":
    raise SystemExit(main())
