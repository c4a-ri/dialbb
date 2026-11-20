#!/usr/bin/env python3
"""Relay utterances and membership changes for an open conversation."""

import argparse
from threading import RLock

import socketio
from werkzeug.serving import run_simple


class Hub:
    def __init__(self):
        self.joined = {}
        self.lock = RLock()
        self.sio = socketio.Server(async_mode="threading")
        self.app = socketio.WSGIApp(self.sio)
        self.sio.on("join", self.join)
        self.sio.on("utterance", self.utterance)
        self.sio.on("disconnect", self.disconnect)

    @property
    def participants(self):
        return list(self.joined.values())

    def join(self, sid, data):
        name = data.get("speaker")
        with self.lock:
            if not isinstance(name, str) or not name.strip():
                return {"error": "participant name must be a nonempty string"}
            if sid in self.joined:
                return {"ok": True} if self.joined[sid] == name else {"error": "already joined with another name"}
            if name in self.joined.values() and self.joined.get(sid) != name:
                return {"error": "participant already joined"}
            self.joined[sid] = name
            self.sio.enter_room(sid, "participants")
            print(f"{name} joined.", flush=True)
            self.sio.emit("participant_joined", {"speaker": name, "participants": self.participants},
                          room="participants")
            return {"ok": True}

    def utterance(self, sid, data):
        with self.lock:
            if sid not in self.joined or self.joined[sid] != data.get("speaker"):
                return {"error": "join the conversation first"}
            utterance = data.get("utterance")
            if not isinstance(utterance, str) or not utterance.strip():
                return {"error": "empty utterance"}
            message = {"speaker": self.joined[sid], "utterance": utterance,
                       "participants": self.participants}
            print(f"{message['speaker']}: {utterance}", flush=True)
            self.sio.emit("broadcast_utterance", message, room="participants")
            return {"ok": True}

    def disconnect(self, sid, reason=None):
        with self.lock:
            name = self.joined.pop(sid, None)
            if name is not None:
                self.sio.leave_room(sid, "participants")
                print(f"{name} left.", flush=True)
                self.sio.emit("participant_left", {"speaker": name, "participants": self.participants},
                              room="participants")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    hub = Hub()
    run_simple(args.host, args.port, hub.app, threaded=True)


if __name__ == "__main__":
    main()
