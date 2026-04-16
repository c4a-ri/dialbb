import time
from queue import Empty, Queue
from threading import Event

from dialbb.util.logger import get_logger
from mm_client.main.messages import TtsRequest, TtsResult


logger = get_logger(__name__)


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
            # Main から渡された読み上げ要求を待つ。
            request = tts_request_queue.get(timeout=0.1)
        except Empty:
            continue

        # ここは仮実装。実際の TTS API 呼び出しに置き換える想定。
        logger.info("[TTS] 合成開始: %s", request.text)
        time.sleep(0.2)
        logger.info("[TTS] 合成完了: %s", request.text)

        tts_result_queue.put(
            # 完了通知を Main へ返す。
            TtsResult(
                session_id=request.session_id,
                text=request.text,
                completed=True,
            )
        )
