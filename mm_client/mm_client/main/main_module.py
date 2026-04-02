import re
from queue import Empty, Queue
from threading import Event

from main.messages import (
    DialbbRequest,
    DialbbResponse,
    RecognitionEvent,
    RecognitionEventType,
    TtsRequest,
    TtsResult,
)


class MultimodalMainModule:
    """Main module worker that mediates modules via queues."""

    def __init__(self, session_id: str = "phase1-session") -> None:
        self.session_id = session_id
        self.final_transcripts: list[str] = []

    def run(
        self,
        stt_event_queue: "Queue[RecognitionEvent]",
        dialbb_request_queue: "Queue[DialbbRequest]",
        dialbb_response_queue: "Queue[DialbbResponse]",
        tts_request_queue: "Queue[TtsRequest]",
        tts_result_queue: "Queue[TtsResult]",
        stop_event: Event,
    ) -> None:
        while not stop_event.is_set():
            self._process_dialbb_responses(
                dialbb_response_queue=dialbb_response_queue,
                tts_request_queue=tts_request_queue,
            )
            self._process_tts_results(tts_result_queue=tts_result_queue)

            try:
                stt_event = stt_event_queue.get(timeout=0.1)
            except Empty:
                continue

            should_stop = self._handle_stt_event(
                event=stt_event,
                dialbb_request_queue=dialbb_request_queue,
            )
            if should_stop:
                stop_event.set()

    def _handle_stt_event(
        self,
        event: RecognitionEvent,
        dialbb_request_queue: "Queue[DialbbRequest]",
    ) -> bool:
        if event.event_type == RecognitionEventType.SPEECH_STARTED:
            print("\n[MAIN] 発話開始")
            return False

        if event.event_type == RecognitionEventType.SPEECH_ENDED:
            print("\n[MAIN] 発話終了")
            return False

        if event.event_type == RecognitionEventType.PARTIAL_TRANSCRIPT:
            print(f"認識中... {event.text}", end="\r", flush=True)
            return False

        if event.event_type == RecognitionEventType.FINAL_TRANSCRIPT:
            text = event.text.strip()
            self.final_transcripts.append(text)
            print(f"\n[MAIN] 確定結果: {text}")

            if re.search(r"\b(終了|ストップ|おしまい)\b", text, re.I):
                print("[MAIN] 終了コマンドを検知。フェーズ1を終了します。")
                return True

            dialbb_request_queue.put(
                DialbbRequest(session_id=self.session_id, user_text=text)
            )
            return False

        if event.event_type == RecognitionEventType.ERROR:
            print(f"\n[MAIN][ERROR] {event.text}")
            return True

        return False

    def _process_dialbb_responses(
        self,
        dialbb_response_queue: "Queue[DialbbResponse]",
        tts_request_queue: "Queue[TtsRequest]",
    ) -> None:
        while True:
            try:
                dialbb_response = dialbb_response_queue.get_nowait()
            except Empty:
                return

            print(f"[MAIN] DialBB応答: {dialbb_response.system_text}")
            tts_request_queue.put(
                TtsRequest(
                    session_id=dialbb_response.session_id,
                    text=dialbb_response.system_text,
                )
            )

    def _process_tts_results(self, tts_result_queue: "Queue[TtsResult]") -> None:
        while True:
            try:
                tts_result = tts_result_queue.get_nowait()
            except Empty:
                return

            if tts_result.completed:
                print(f"[MAIN] 音声合成完了: {tts_result.text}")
