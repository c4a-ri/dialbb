#!/usr/bin/env python3
"""Relay utterances and membership changes for an open conversation."""

import argparse
from functools import partial
from threading import Event, RLock

import socketio
from werkzeug.serving import make_server, run_simple


class Hub:
    def __init__(self, max_turns=None):
        if max_turns is not None and (type(max_turns) is not int or max_turns < 1):
            raise ValueError("max_turns must be a positive integer")
        self._max_turns = max_turns
        self._turns = 0
        self._connected = set()
        self._pending_final_delivery = set()
        self._final_sent = Event()
        self._final_delivered = Event()
        self.joined = {}
        self.lock = RLock()
        # For a limited conversation, send the final caller's ACK before handling
        # any delivery acknowledgement or disconnect from that connection.
        self.sio = socketio.Server(async_mode="threading", async_handlers=max_turns is None)
        self.app = socketio.WSGIApp(self.sio)
        self.sio.on("connect", self.connect)
        self.sio.on("join", self.join)
        self.sio.on("utterance", self.utterance)
        self.sio.on("disconnect", self.disconnect)

    @property
    def participants(self):
        return list(self.joined.values())

    @property
    def _finished(self):
        return self._turns == self._max_turns

    def connect(self, sid, environ, auth=None):
        with self.lock:
            if self._finished:
                return False
            self._connected.add(sid)

    def join(self, sid, data):
        name = data.get("speaker")
        with self.lock:
            if self._finished:
                return {"error": "conversation has ended"}
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
            if self._finished:
                return {"error": "conversation has ended", "conversation_ended": True}
            if sid not in self.joined or self.joined[sid] != data.get("speaker"):
                return {"error": "join the conversation first"}
            utterance = data.get("utterance")
            if not isinstance(utterance, str) or not utterance.strip():
                return {"error": "empty utterance"}
            message = {"speaker": self.joined[sid], "utterance": utterance,
                       "participants": self.participants}
            self._turns += 1
            print(f"{message['speaker']}: {utterance}", flush=True)
            if self._finished:
                self._send_final_utterance(message)
            else:
                self.sio.emit("broadcast_utterance", message, room="participants")
            return {"ok": True}

    def _send_final_utterance(self, message):
        message["conversation_ended"] = True
        recipients = self._connected | self.joined.keys()
        self._pending_final_delivery.update(recipients)
        for sid in recipients:
            # Socket.IO callbacks acknowledge delivery to one connection at a time.
            callback = partial(self._acknowledge_final_delivery, sid)
            if sid in self.joined:
                self.sio.emit("broadcast_utterance", message, to=sid, callback=callback)
            else:
                self.sio.emit("conversation_ended", to=sid, callback=callback)
        print(f"Conversation ended after {self._turns} turns.", flush=True)
        self._final_sent.set()

    def _acknowledge_final_delivery(self, sid, *args):
        with self.lock:
            self._pending_final_delivery.discard(sid)
            if self._finished and not self._pending_final_delivery:
                self._final_delivered.set()

    def shutdown_at_turn_limit(self, server):
        self._final_sent.wait()
        # Unresponsive clients must not keep the hub running indefinitely.
        self._final_delivered.wait(timeout=3)
        with self.lock:
            connected = list(self._connected)
        for sid in connected:
            self.sio.disconnect(sid)
        self.sio.shutdown()
        server.shutdown()

    def disconnect(self, sid, reason=None):
        with self.lock:
            self._connected.discard(sid)
            self._acknowledge_final_delivery(sid)
            name = self.joined.pop(sid, None)
            if name is not None:
                self.sio.leave_room(sid, "participants")
                print(f"{name} left.", flush=True)
                if not self._finished:
                    self.sio.emit("participant_left", {"speaker": name, "participants": self.participants},
                                  room="participants")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--max-turns", type=int,
                        help="End the conversation after this many utterances (default: unlimited).")
    args = parser.parse_args()
    try:
        hub = Hub(max_turns=args.max_turns)
    except ValueError as error:
        parser.error(str(error))
    if args.max_turns is None:
        run_simple(args.host, args.port, hub.app, threaded=True)
    else:
        with make_server(args.host, args.port, hub.app, threaded=True) as server:
            server.log_startup()
            hub.sio.start_background_task(hub.shutdown_at_turn_limit, server)
            server.serve_forever()


if __name__ == "__main__":
    main()
