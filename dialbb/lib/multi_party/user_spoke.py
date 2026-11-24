#!/usr/bin/env python3
"""Command-line participant for a multi-party conversation."""

import argparse
import sys
from threading import Event, Thread

import socketio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("my_name")
    parser.add_argument("--hub-url", default="http://localhost:5000")
    args = parser.parse_args()
    sio = socketio.Client(reconnection=False)
    stopped = Event()
    input_error = None

    @sio.on("disconnect")
    def disconnected(*args):
        stopped.set()

    @sio.on("conversation_ended")
    def conversation_ended():
        print("\nConversation ended.", flush=True)
        stopped.set()

    @sio.on("broadcast_utterance")
    def receive_utterance(data):
        if data.get("conversation_ended"):
            print(f"\n{data['speaker']}: {data['utterance']}", flush=True)
            conversation_ended()
            return
        print(f"\n{data['speaker']}: {data['utterance']}\nyou> ", end="", flush=True)

    @sio.on("participant_joined")
    def participant_joined(data):
        print(f"\n{data['speaker']} joined. Participants: {', '.join(data['participants'])}", flush=True)

    @sio.on("participant_left")
    def participant_left(data):
        print(f"\n{data['speaker']} left. Participants: {', '.join(data['participants'])}", flush=True)

    def read_input():
        nonlocal input_error
        try:
            # Use a private buffer so a blocked read cannot hold the standard
            # input buffer's lock while the interpreter exits.
            with open(sys.stdin.fileno(), encoding=sys.stdin.encoding, errors=sys.stdin.errors,
                      closefd=False) as stream:
                print("press enter to join the conversation> ", end="", flush=True)
                if not stream.readline() or stopped.is_set():
                    return
                result = sio.call("join", {"speaker": args.my_name})
                if result and result.get("error"):
                    raise RuntimeError(result["error"])
                while not stopped.is_set():
                    print("you> ", end="", flush=True)
                    line = stream.readline()
                    if not line or stopped.is_set():
                        break
                    utterance = line.rstrip("\n")
                    if utterance.strip():
                        result = sio.call("utterance", {"speaker": args.my_name, "utterance": utterance})
                        if result and result.get("error"):
                            print(result["error"], flush=True)
        except (OSError, RuntimeError, socketio.exceptions.SocketIOError) as error:
            if not stopped.is_set():
                input_error = error
        finally:
            stopped.set()

    try:
        sio.connect(args.hub_url)
        Thread(target=read_input, daemon=True).start()
        while not stopped.wait(0.25):
            pass
        if input_error is not None:
            raise input_error
    except KeyboardInterrupt:
        pass
    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
