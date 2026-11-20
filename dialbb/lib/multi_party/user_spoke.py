#!/usr/bin/env python3
"""Command-line participant for a multi-party conversation."""

import argparse

import socketio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("my_name")
    parser.add_argument("--hub-url", default="http://localhost:5000")
    args = parser.parse_args()
    sio = socketio.Client(reconnection=False)

    @sio.on("broadcast_utterance")
    def receive_utterance(data):
        print(f"\n{data['speaker']}: {data['utterance']}\nyou> ", end="", flush=True)

    @sio.on("participant_joined")
    def participant_joined(data):
        print(f"\n{data['speaker']} joined. Participants: {', '.join(data['participants'])}", flush=True)

    @sio.on("participant_left")
    def participant_left(data):
        print(f"\n{data['speaker']} left. Participants: {', '.join(data['participants'])}", flush=True)

    try:
        sio.connect(args.hub_url)
        input("press enter to join the conversation> ")
        result = sio.call("join", {"speaker": args.my_name})
        if result and result.get("error"):
            raise RuntimeError(result["error"])
        while sio.connected:
            utterance = input("you> ")
            if utterance.strip():
                result = sio.call("utterance", {"speaker": args.my_name, "utterance": utterance})
                if result and result.get("error"):
                    print(result["error"])
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
