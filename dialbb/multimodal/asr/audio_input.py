import platform
import queue
from threading import Event

import numpy as np

try:
    import pyaudio
except ImportError as pyaudio_import_error:
    if platform.system() == "Windows":
        try:
            import pyaudiowpatch as pyaudio
        except ImportError as windows_fallback_error:
            raise ImportError(
                "Audio input backend is missing. Install 'pyaudiowpatch' on Windows."
            ) from windows_fallback_error
    else:
        raise ImportError(
            "Audio input backend is missing. Install 'pyaudio'. "
            "On macOS, install PortAudio first (e.g. 'brew install portaudio')."
        ) from pyaudio_import_error


class MicrophoneAudioInput:
    """Capture microphone input and provide PCM16 chunks via generator."""

    def __init__(self, sample_rate: int = 16000, chunk_ms: int = 100, gain: float = 1.0) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        # gain: 1.0=原音, <1.0=減衰, >1.0=増幅。例: 0.3 で約70%減衰。
        self._gain = max(0.0, gain)
        self._buffer: "queue.Queue[bytes | None]" = queue.Queue()
        self.closed = True

    def __enter__(self) -> "MicrophoneAudioInput":
        # 非同期コールバックで受けた音声データを内部キューへ積む。
        self._audio_interface = pyaudio.PyAudio()
        # input=True でマイク入力ストリームを開く。
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # ストリーム停止後に終端マーカー(None)を積んで consumer を終了させる。
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buffer.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        # PyAudio コールバックから呼ばれ、受信した生データをキューへ渡す。
        self._buffer.put(in_data)
        return None, pyaudio.paContinue

    def chunks(self):
        while not self.closed:
            chunk = self._buffer.get()
            if chunk is None:
                return

            # 取り出し可能な分をまとめて返し、STT 呼び出し回数を減らす。
            data = [chunk]
            while True:
                try:
                    chunk = self._buffer.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            raw = b"".join(data)
            # gain が 1.0 以外のときだけスケーリングする（PCM16 = 2 bytes/sample）。
            if self._gain != 1.0:
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                samples *= self._gain
                raw = np.clip(samples, -32768, 32767).astype(np.int16).tobytes()
            yield raw


class WebSocketAudioInput:
    """WebSocket 経由で受信した PCM16 音声チャンクを STT へ供給するアダプタ。

    クライアント（スマホ/ブラウザ）から送られてきた音声バイト列を
    audio_queue 経由で受け取り、STT ストリームへ逐次供給する。
    enabled_event または stop_event がセットされた場合はストリームを終了する。
    """

    def __init__(
        self,
        audio_queue: "queue.Queue[bytes | None]",
        enabled_event: "Event | None" = None,
        stop_event: "Event | None" = None,
    ) -> None:
        self._queue = audio_queue
        self._enabled_event = enabled_event
        self._stop_event = stop_event

    def chunks(self) -> "Generator[bytes, None, None]":
        """音声チャンクを逐次 yield する。停止条件を満たしたら終了。"""
        while True:
            if self._stop_event and self._stop_event.is_set():
                return
            if self._enabled_event and not self._enabled_event.is_set():
                return
            try:
                chunk = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if chunk is None:
                return
            yield chunk
