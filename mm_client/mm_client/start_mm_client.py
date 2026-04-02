import queue
import threading

from asr.google_stt_client import run_stt_worker
from main.dialbb_client import run_dialbb_worker
from main.main_module import MultimodalMainModule
from main.messages import DialbbRequest, DialbbResponse, RecognitionEvent, TtsRequest, TtsResult
from tts.speech_synthesizer import run_tts_worker


def main() -> None:
    print("[SYSTEM] 起動: 4スレッド構成 (Main / STT / DialBB / TTS)")
    print("[SYSTEM] マイクに向かって話してください（終了するには『終了』）")

    stop_event = threading.Event()

    stt_event_queue: "queue.Queue[RecognitionEvent]" = queue.Queue()
    dialbb_request_queue: "queue.Queue[DialbbRequest]" = queue.Queue()
    dialbb_response_queue: "queue.Queue[DialbbResponse]" = queue.Queue()
    tts_request_queue: "queue.Queue[TtsRequest]" = queue.Queue()
    tts_result_queue: "queue.Queue[TtsResult]" = queue.Queue()

    main_module = MultimodalMainModule()

    workers = [
        threading.Thread(
            target=run_stt_worker,
            kwargs={
                "stt_event_queue": stt_event_queue,
                "stop_event": stop_event,
                "sample_rate": 16000,
                "chunk_ms": 100,
                "language_code": "ja-JP",
            },
            name="stt-worker",
            daemon=True,
        ),
        threading.Thread(
            target=run_dialbb_worker,
            kwargs={
                "dialbb_request_queue": dialbb_request_queue,
                "dialbb_response_queue": dialbb_response_queue,
                "stop_event": stop_event,
            },
            name="dialbb-worker",
            daemon=True,
        ),
        threading.Thread(
            target=run_tts_worker,
            kwargs={
                "tts_request_queue": tts_request_queue,
                "tts_result_queue": tts_result_queue,
                "stop_event": stop_event,
            },
            name="tts-worker",
            daemon=True,
        ),
        threading.Thread(
            target=main_module.run,
            kwargs={
                "stt_event_queue": stt_event_queue,
                "dialbb_request_queue": dialbb_request_queue,
                "dialbb_response_queue": dialbb_response_queue,
                "tts_request_queue": tts_request_queue,
                "tts_result_queue": tts_result_queue,
                "stop_event": stop_event,
            },
            name="main-module-worker",
            daemon=True,
        ),
    ]

    for worker in workers:
        worker.start()

    try:
        while not stop_event.is_set():
            workers[3].join(timeout=0.2)
            if not workers[3].is_alive():
                stop_event.set()
                break
    except KeyboardInterrupt:
        print("\n[SYSTEM] Ctrl+C を受信。終了処理を開始します。")
        stop_event.set()

    print("[SYSTEM] 停止しました。")


if __name__ == "__main__":
    main()
