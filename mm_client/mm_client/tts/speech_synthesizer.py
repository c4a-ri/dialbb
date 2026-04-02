import time
from queue import Empty, Queue
from threading import Event

from main.messages import TtsRequest, TtsResult


def run_tts_worker(
    tts_request_queue: "Queue[TtsRequest]",
    tts_result_queue: "Queue[TtsResult]",
    stop_event: Event,
) -> None:
    """Speech synthesis worker thread.

    Current implementation is a placeholder. Replace this with real TTS API integration.
    """
    while not stop_event.is_set():
        try:
            request = tts_request_queue.get(timeout=0.1)
        except Empty:
            continue

        print(f"[TTS] 合成開始: {request.text}")
        time.sleep(0.2)
        print(f"[TTS] 合成完了: {request.text}")

        tts_result_queue.put(
            TtsResult(
                session_id=request.session_id,
                text=request.text,
                completed=True,
            )
        )
