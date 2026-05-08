import audioop
import queue

try:
    import pyaudio
except ImportError:  # Windows fallback
    import pyaudiowpatch as pyaudio


class MicrophoneAudioInput:
    """Capture microphone input and provide PCM16 chunks via generator."""

    def __init__(self, sample_rate: int = 16000, chunk_ms: int = 100, gain: float = 1.0) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        # gain: 1.0=原音, <1.0=減衰, >1.0=増幅。例: 0.3 で約70%減衰。
        self._gain = max(0.0, gain)
        self._buffer: "queue.Queue[bytes | None]" = queue.Queue()
        self.closed = True

    def __enter__(self):
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
                raw = audioop.mul(raw, 2, self._gain)
            yield raw
