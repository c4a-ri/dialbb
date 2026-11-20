#!/usr/bin/env python3
"""GUI participant with a separate input field for Japanese IME composition."""

import argparse
from queue import Empty, Queue

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)
import socketio


class MessageInput(QLineEdit):
    send_requested = Signal()

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            QApplication.inputMethod().commit()
            self.send_requested.emit()
            event.accept()
            return
        # Let Qt/Windows handle IME conversion and confirmation with Enter.
        super().keyPressEvent(event)


class UserSpokeWindow(QWidget):
    def __init__(self, sio, my_name):
        super().__init__()
        self.sio = sio
        self.my_name = my_name
        self.joined = False
        self.events = Queue()
        self.setWindowTitle(f"DialBB multi-party: {my_name}")
        self.resize(900, 600)
        self.history = QTextEdit(readOnly=True)
        self.entry = MessageInput()
        self.entry.setPlaceholderText("日本語を入力（Enter は変換確定、Ctrl+Enter は送信）")
        self.join_button = QPushButton(f"Join as {my_name}")
        self.send_button = QPushButton("Send (Ctrl+Enter)")
        self.send_button.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self.history)
        layout.addWidget(self.entry)
        buttons = QHBoxLayout()
        buttons.addWidget(self.join_button)
        buttons.addWidget(self.send_button)
        layout.addLayout(buttons)
        self.join_button.clicked.connect(self.join)
        self.send_button.clicked.connect(self.send)
        self.entry.send_requested.connect(self.send)
        self.sio.on("broadcast_utterance", self.receive_utterance)
        self.sio.on("participant_joined", self.participant_joined)
        self.sio.on("participant_left", self.participant_left)
        self.sio.on("disconnect", lambda *args: self.events.put(("disconnect", None)))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

    def receive_utterance(self, data):
        self.events.put(("message", f"{data['speaker']}: {data['utterance']}"))

    def participant_joined(self, data):
        self.events.put(("message", f"{data['speaker']} joined. Participants: {', '.join(data['participants'])}"))

    def participant_left(self, data):
        self.events.put(("message", f"{data['speaker']} left. Participants: {', '.join(data['participants'])}"))

    def join(self):
        self.join_button.setEnabled(False)
        self.sio.emit("join", {"speaker": self.my_name},
                      callback=lambda result: self.events.put(("joined", result)))

    def send(self):
        utterance = self.entry.text().strip()
        if self.joined and self.sio.connected and utterance:
            self.sio.emit("utterance", {"speaker": self.my_name, "utterance": utterance},
                          callback=lambda result: self.events.put(("result", result)))
            self.entry.clear()
            self.entry.setFocus()

    def poll(self):
        # Socket.IO callbacks run outside the GUI thread. Only this timer updates widgets.
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "message":
                    self.history.insertPlainText(data + "\n")
                    self.history.ensureCursorVisible()
                elif kind in ("joined", "result"):
                    error = (data or {}).get("error")
                    if error:
                        self.history.insertPlainText(error + "\n")
                        if kind == "joined":
                            self.join_button.setEnabled(True)
                    elif kind == "joined":
                        self.joined = True
                        self.send_button.setEnabled(True)
                        self.entry.setFocus()
                elif kind == "disconnect":
                    self.joined = False
                    self.send_button.setEnabled(False)
                    self.history.insertPlainText("Disconnected from the hub.\n")
        except Empty:
            pass

    def closeEvent(self, event):
        self.timer.stop()
        if self.sio.connected:
            self.sio.disconnect()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("my_name")
    parser.add_argument("--hub-url", default="http://localhost:5000")
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    sio = socketio.Client(reconnection=False)
    window = UserSpokeWindow(sio, args.my_name)
    try:
        sio.connect(args.hub_url)
        window.show()
        window.entry.setFocus()
        app.exec()
    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
