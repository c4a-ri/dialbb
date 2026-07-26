from __future__ import annotations

import asyncio
import io
import threading
import time
import wave
from dataclasses import dataclass, field
from fractions import Fraction
from queue import Empty as QueueEmpty
from typing import Callable

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
from av import AudioFrame, AudioResampler

from dialbb.util.logger import get_logger
from .tts.speech_synthesizer import TTS_SAMPLE_RATE_HZ


logger = get_logger(__name__)

WEBRTC_SAMPLE_RATE_HZ = TTS_SAMPLE_RATE_HZ
WEBRTC_CHANNELS = 1
WEBRTC_SAMPLE_WIDTH_BYTES = 2
WEBRTC_FRAME_DURATION_MS = 20
WEBRTC_FRAME_SAMPLES = WEBRTC_SAMPLE_RATE_HZ * WEBRTC_FRAME_DURATION_MS // 1000
WEBRTC_FRAME_BYTES = WEBRTC_FRAME_SAMPLES * WEBRTC_CHANNELS * WEBRTC_SAMPLE_WIDTH_BYTES


@dataclass
class _QueuedAudioFrame:
    pcm_bytes: bytes
    playback_event: threading.Event | None = None


class OutgoingAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._loop = loop
        self._queue: asyncio.Queue[_QueuedAudioFrame | None] = asyncio.Queue()
        self._start_time: float | None = None
        self._timestamp = 0

    def enqueue_pcm_chunk(self, pcm_bytes: bytes) -> threading.Event:
        playback_event = threading.Event()
        frames = self._split_pcm_frames(pcm_bytes)
        if not frames:
            playback_event.set()
            return playback_event

        payloads = [_QueuedAudioFrame(frame_bytes) for frame_bytes in frames[:-1]]
        payloads.append(_QueuedAudioFrame(frames[-1], playback_event=playback_event))

        def _enqueue() -> None:
            if self._queue.empty():
                self._start_time = None
                self._timestamp = 0
            for payload in payloads:
                self._queue.put_nowait(payload)

        self._loop.call_soon_threadsafe(_enqueue)
        return playback_event

    def clear(self) -> None:
        def _clear() -> None:
            while True:
                try:
                    payload = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if payload is not None and payload.playback_event is not None:
                    payload.playback_event.set()
            self._start_time = None
            self._timestamp = 0

        self._loop.call_soon_threadsafe(_clear)

    def close(self) -> None:
        self.clear()

        def _close() -> None:
            self._queue.put_nowait(None)

        self._loop.call_soon_threadsafe(_close)

    async def recv(self) -> AudioFrame:
        payload = await self._queue.get()
        if payload is None:
            self.stop()
            raise MediaStreamError

        sample_count = len(payload.pcm_bytes) // WEBRTC_SAMPLE_WIDTH_BYTES
        if self._start_time is None:
            self._start_time = time.monotonic()
            self._timestamp = 0
        else:
            self._timestamp += sample_count
            wait = self._start_time + (self._timestamp / WEBRTC_SAMPLE_RATE_HZ) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)

        frame = AudioFrame(format="s16", layout="mono", samples=sample_count)
        frame.planes[0].update(payload.pcm_bytes)
        frame.sample_rate = WEBRTC_SAMPLE_RATE_HZ
        frame.time_base = Fraction(1, WEBRTC_SAMPLE_RATE_HZ)
        frame.pts = self._timestamp

        if payload.playback_event is not None:
            payload.playback_event.set()

        return frame

    @staticmethod
    def _split_pcm_frames(pcm_bytes: bytes) -> list[bytes]:
        if not pcm_bytes:
            return []

        frames: list[bytes] = []
        for offset in range(0, len(pcm_bytes), WEBRTC_FRAME_BYTES):
            frame_bytes = pcm_bytes[offset:offset + WEBRTC_FRAME_BYTES]
            if len(frame_bytes) < WEBRTC_FRAME_BYTES:
                frame_bytes = frame_bytes.ljust(WEBRTC_FRAME_BYTES, b"\x00")
            frames.append(frame_bytes)
        return frames


@dataclass
class WebRtcAudioSession:
    peer_connection: RTCPeerConnection
    outgoing_track: OutgoingAudioTrack
    incoming_tasks: set[asyncio.Task[None]] = field(default_factory=set)

    def add_task(self, task: asyncio.Task[None]) -> None:
        self.incoming_tasks.add(task)
        task.add_done_callback(self.incoming_tasks.discard)

    async def close(self) -> None:
        self.outgoing_track.close()
        for task in list(self.incoming_tasks):
            task.cancel()
        if self.incoming_tasks:
            await asyncio.gather(*self.incoming_tasks, return_exceptions=True)
        await self.peer_connection.close()


def decode_wav_audio_bytes(audio_bytes: bytes) -> tuple[bytes, int, int, int]:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        return (
            wav_file.readframes(wav_file.getnframes()),
            wav_file.getframerate(),
            wav_file.getnchannels(),
            wav_file.getsampwidth(),
        )


async def consume_incoming_audio_track(
    track: MediaStreamTrack,
    on_audio_chunk: Callable[[bytes], None],
) -> None:
    resampler = AudioResampler(format="s16", layout="mono", rate=WEBRTC_SAMPLE_RATE_HZ)

    try:
        while True:
            frame = await track.recv()
            resampled = resampler.resample(frame)
            frames = resampled if isinstance(resampled, list) else [resampled]
            for output_frame in frames:
                if output_frame is None:
                    continue
                pcm_bytes = bytes(output_frame.planes[0])
                if pcm_bytes:
                    on_audio_chunk(pcm_bytes)
    except asyncio.CancelledError:
        raise
    except MediaStreamError:
        logger.info("[WEBRTC] incoming audio track ended")
    except Exception:
        logger.exception("[WEBRTC] incoming audio track failed")