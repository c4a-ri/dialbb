#!/usr/bin/env python3
"""Connect a DialBB application to the multi-party hub."""

import argparse
import logging
import math
from queue import Empty, Queue
from threading import Event, RLock, Thread
import time

import socketio
import yaml

from dialbb.lib.multi_party.events import JOINED, LEFT, SILENCE

class DialBBSpoke:
    def __init__(self, dialogue_processor, my_name, silence_timeout=0):
        if (isinstance(silence_timeout, bool) or not isinstance(silence_timeout, (int, float))
                or not math.isfinite(silence_timeout) or silence_timeout < 0):
            raise ValueError("silence_timeout must be a nonnegative number of seconds")
        self.dialogue_processor = dialogue_processor
        self.my_name = my_name
        self.session_id = ""
        self.error = None
        self.silence_timeout = silence_timeout
        self.participants = []
        self._state_lock = RLock()
        self._next_silence_at = None
        self._conversation_ended = Event()
        self.sio = socketio.Client(reconnection=False)
        self.events = Queue()
        self.worker = Thread(target=self._process_events, daemon=True)
        self.sio.on("participant_joined", lambda data: self._receive_event("joined", data))
        self.sio.on("participant_left", lambda data: self._receive_event("left", data))
        self.sio.on("broadcast_utterance", lambda data: self._receive_event("utterance", data))
        self.sio.on("conversation_ended", self._finish_conversation)

    def _receive_event(self, kind, data):
        if data.get("conversation_ended"):
            self._finish_conversation()
            return
        with self._state_lock:
            self.participants = list(data["participants"])
            # All actual utterances, including echoes of our own speech, reset
            # the timer immediately, even while a DialBB request is running.
            if kind == "utterance" and data.get("utterance", "").strip() and self.silence_timeout:
                self._next_silence_at = time.monotonic() + self.silence_timeout
            self.events.put((kind, data))

    def _finish_conversation(self):
        self._conversation_ended.set()
        self.events.put(None)

    def _silence_wait_time(self):
        with self._state_lock:
            if not self.sio.connected or not self.silence_timeout or self._next_silence_at is None:
                return None
            return max(0, self._next_silence_at - time.monotonic())

    def _silence_event(self):
        with self._state_lock:
            if (not self.sio.connected or not self.silence_timeout or self._next_silence_at is None
                    or time.monotonic() < self._next_silence_at):
                return None
            self._next_silence_at = time.monotonic() + self.silence_timeout
            return ("silence", {"speaker": "", "utterance": SILENCE,
                                "participants": list(self.participants)})

    def connect(self, hub_url, *, background=False):
        self.sio.connect(hub_url)
        if background:
            self.worker = Thread(target=self._initialize_and_process_events, daemon=True)
        else:
            self._initialize()
        self.worker.start()

    def _initialize_and_process_events(self):
        try:
            self._initialize()
        except (Exception, SystemExit) as error:
            if not self._conversation_ended.is_set():
                self.error = error
                logging.exception("Failed to initialize the multi-party dialogue")
                self.sio.disconnect()
            return
        self._process_events()

    def _initialize(self):
        # Initialize the DialBB session immediately after connecting. Join next,
        # before publishing a possible initial utterance. Membership events are
        # queued until initialization and registration have both completed.
        response = self.dialogue_processor.process({
            "user_id": self.my_name, "aux_data": {"participants": []}}, initial=True)
        if self._conversation_ended.is_set():
            return
        self.session_id = response["session_id"]
        result = self.sio.call("join", {"speaker": self.my_name})
        if result and result.get("error"):
            self.sio.disconnect()
            raise RuntimeError(result["error"])
        with self._state_lock:
            if self.silence_timeout:
                self._next_silence_at = time.monotonic() + self.silence_timeout
        self._send_response(response)

    def _send_response(self, response):
        if self._conversation_ended.is_set():
            return
        utterance = response.get("system_utterance")
        if utterance and self.sio.connected:
            result = self.sio.call("utterance", {"speaker": self.my_name, "utterance": utterance})
            if result and result.get("conversation_ended"):
                self._finish_conversation()
            elif result and result.get("error"):
                raise RuntimeError(result["error"])
        elif self.sio.connected:
            print(f"{self.my_name}: waiting (no utterance).", flush=True)

    def _process_events(self):
        # Socket.IO callbacks run in separate threads. Process all DialBB requests
        # on one worker so slow API calls cannot overwrite conversation state.
        while True:
            queued = True
            try:
                event = self.events.get(timeout=self._silence_wait_time())
            except Empty:
                event = self._silence_event()
                if event is None:
                    continue
                queued = False
            try:
                if self._conversation_ended.is_set():
                    if self.sio.connected:
                        self.sio.disconnect()
                    return
                if event is None:
                    return
                kind, data = event
                if kind == "utterance" and data["speaker"] == self.my_name:
                    continue
                utterance = JOINED if kind == "joined" else LEFT if kind == "left" else data["utterance"]
                aux_data = {"participants": list(data["participants"])}
                print(f"{self.my_name}: processing {kind} from {data['speaker'] or 'silence timer'}...", flush=True)
                response = self.dialogue_processor.process({
                    "user_id": data["speaker"], "user_utterance": utterance,
                    "session_id": self.session_id,
                    "aux_data": aux_data,
                })
                self._send_response(response)
                if kind == "silence":
                    # Never queue repeated timeouts during a slow LLM call.
                    with self._state_lock:
                        self._next_silence_at = time.monotonic() + self.silence_timeout
            except (Exception, SystemExit) as error:
                if self._conversation_ended.is_set():
                    return
                self.error = error
                logging.exception("Failed to process a multi-party dialogue event")
                # A partial request may have changed the dialogue history.
                # Disconnect instead of continuing with inconsistent state.
                self.sio.disconnect()
                return
            finally:
                if queued:
                    self.events.task_done()

    def close(self):
        if self.sio.connected:
            self.sio.disconnect()
        self.events.put(None)
        if self.worker.is_alive() and not self._conversation_ended.is_set():
            self.worker.join(timeout=5)


def main():
    from dialbb.main import DialogueProcessor

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_file")
    parser.add_argument("my_name")
    parser.add_argument("--hub-url", default="http://localhost:5000")
    args = parser.parse_args()
    with open(args.config_file, encoding="utf-8") as fp:
        config = yaml.safe_load(fp)
    spoke = DialBBSpoke(DialogueProcessor(args.config_file, {"my_name": args.my_name}), args.my_name,
                       silence_timeout=config.get("silence_timeout", 0))
    try:
        spoke.connect(args.hub_url, background=True)
        spoke.sio.wait()
        if spoke.error is not None:
            raise SystemExit(1)
    except KeyboardInterrupt:
        pass
    finally:
        spoke.close()


if __name__ == "__main__":
    main()
