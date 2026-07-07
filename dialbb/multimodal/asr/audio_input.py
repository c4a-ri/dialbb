from collections.abc import Generator
import queue
class WebSocketAudioInput:
    """WebSocket 経由で受信した PCM16 音声チャンクを STT へ供給するアダプタ。

    クライアント（スマホ/ブラウザ）から送られてきた音声バイト列を
    audio_queue 経由で受け取り、STT ストリームへ逐次供給する。
    enabled_event または stop_event がセットされた場合はストリームを終了する。
    """

    def __init__(
        self,
        audio_queue: "queue.Queue[bytes | None]",
        enabled_event: object | None = None,
        stop_event: object | None = None,
    ) -> None:
        self._queue = audio_queue
        self._enabled_event = enabled_event
        self._stop_event = stop_event

    def chunks(self) -> Generator[bytes, None, None]:
        """音声チャンクを逐次 yield する。停止条件を満たしたら終了。"""
        while True:
            if self._stop_event and getattr(self._stop_event, "is_set", lambda: False)():
                return
            if self._enabled_event and not getattr(self._enabled_event, "is_set", lambda: True)():
                return
            try:
                chunk = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if chunk is None:
                return
            yield chunk
