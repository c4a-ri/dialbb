import io
import threading
import wave
from queue import Empty, Queue
from threading import Event
from typing import Callable, cast

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import texttospeech

from dialbb.util.logger import get_logger
from ..main.messages import TtsRequest, TtsResult


logger = get_logger(__name__)

_LANGUAGE_CODE = "ja-JP"
_VOICE_NAME = "ja-JP-Neural2-B"
TTS_AUDIO_FORMAT = "wav"
TTS_SAMPLE_RATE_HZ = 16000
TTS_CHUNK_MILLISECONDS = 100
_AUDIO_ENCODING: texttospeech.AudioEncoding = cast(
    texttospeech.AudioEncoding,
    texttospeech.AudioEncoding.LINEAR16,
)


def _synthesize_with_encoding(
    client: texttospeech.TextToSpeechClient,
    text: str,
    audio_encoding: texttospeech.AudioEncoding,
) -> bytes:
    """Run Google Cloud TTS synthesis with the specified encoding."""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=_LANGUAGE_CODE,
        name=_VOICE_NAME,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=audio_encoding,
        sample_rate_hertz=TTS_SAMPLE_RATE_HZ,
    )
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return response.audio_content


def _synthesize(client: texttospeech.TextToSpeechClient, text: str) -> bytes:
    """Synthesize text with Google Cloud TTS and return bytes in the default format."""
    return _synthesize_with_encoding(client, text, _AUDIO_ENCODING)


def _encode_wav_chunk(
    pcm_bytes: bytes,
    sample_rate_hz: int,
    channels: int,
    sample_width_bytes: int,
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width_bytes)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def _decode_wav_payload(audio_bytes: bytes) -> tuple[bytes, int, int, int]:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            return (
                wav_file.readframes(wav_file.getnframes()),
                wav_file.getframerate(),
                wav_file.getnchannels(),
                wav_file.getsampwidth(),
            )
    except (wave.Error, EOFError):
        return audio_bytes, TTS_SAMPLE_RATE_HZ, 1, 2


def split_tts_audio_chunks(
    audio_bytes: bytes,
    chunk_duration_ms: int = TTS_CHUNK_MILLISECONDS,
) -> list[bytes]:
    """Split synthesized audio into WAV chunks of the specified duration."""
    pcm_bytes, sample_rate_hz, channels, sample_width_bytes = _decode_wav_payload(audio_bytes)
    if not pcm_bytes:
        return []

    frames_per_chunk = max(1, sample_rate_hz * chunk_duration_ms // 1000)
    bytes_per_frame = channels * sample_width_bytes
    chunk_size_bytes = frames_per_chunk * bytes_per_frame
    return [
        _encode_wav_chunk(
            pcm_bytes[offset:offset + chunk_size_bytes],
            sample_rate_hz,
            channels,
            sample_width_bytes,
        )
        for offset in range(0, len(pcm_bytes), chunk_size_bytes)
    ]


def split_tts_segments(text: str) -> list[str]:
    """Treat the full text as a single segment for TTS synthesis."""
    normalized = text.strip()
    return [normalized] if normalized else []


def run_tts_worker(
    tts_request_queue: "Queue[TtsRequest]",
    tts_result_queue: "Queue[TtsResult]",
    stop_event: Event,
    conversation_active_event: "Event | None" = None,
    tts_cancel_queue: "Queue[str] | None" = None,
    cancel_state_clear_callback: Callable[[str], None] | None = None,
    audio_send_callback: Callable[[int, int, bytes], bool] | None = None,
) -> None:
    """Speech synthesis worker thread backed by Google Cloud TTS.

    In client audio mode, each utterance is synthesized as a whole and
    passed to the client through audio_send_callback.
    """
    logger.info("[TTS] worker start: thread=%s", threading.current_thread().name)
    try:
        client = texttospeech.TextToSpeechClient()
        active_event = conversation_active_event or Event()
        if conversation_active_event is None:
            active_event.set()

        if audio_send_callback is None:
            logger.error("[TTS] can't send speech because audio_send_callback is not set.")
            return

        while not stop_event.is_set():
            try:
                request = tts_request_queue.get(timeout=0.1)
            except Empty:
                continue

            if tts_cancel_queue is not None:
                while True:
                    try:
                        tts_cancel_queue.get_nowait()
                    except Empty:
                        break

            logger.info("[TTS] TTS<-MAIN request to synthesize received.")
            logger.debug(f"[TTS] request.text={request.text}")

            segments = split_tts_segments(request.text)
            total_segments: int = len(segments)

            completed = True
            for segment_index, segment in enumerate(segments, start=1):
                if stop_event.is_set() or not active_event.is_set():
                    logger.debug(f"[TTS] canceled: {segment}")
                    completed = False
                    break

                if tts_cancel_queue is not None:
                    cancel_requested = False
                    while True:
                        try:
                            tts_cancel_queue.get_nowait()
                            cancel_requested = True
                        except Empty:
                            break
                    if cancel_requested:
                        logger.info("[TTS] cancel request received: segment=%d/%d", segment_index, total_segments)
                        completed = False
                        break

                logger.debug(f"[TTS] synthesizing: {segment}")
                try:
                    audio_bytes = _synthesize(client, segment)
                except (GoogleAPICallError, RetryError, OSError):
                    logger.exception(f"[TTS] synthesis error: {segment}")
                    completed = False
                    break

                if tts_cancel_queue is not None:
                    cancel_requested = False
                    while True:
                        try:
                            tts_cancel_queue.get_nowait()
                            cancel_requested = True
                        except Empty:
                            break
                    if cancel_requested:
                        logger.info("[TTS] cancel request received (synth後): segment=%d/%d", segment_index, total_segments)
                        completed = False
                        break

                if not audio_send_callback(segment_index, total_segments, audio_bytes):
                    logger.info("[TTS] audio send interrupted: segment=%d/%d", segment_index, total_segments)
                    completed = False
                    break

            tts_result_queue.put(
                TtsResult(
                    session_id=request.session_id,
                    text=request.text,
                    completed=completed,
                )
            )
            logger.info("[TTS] TTS->MAIN 結果送信")
            if completed:
                logger.debug("[TTS] 合成完了: %s", request.text)

            if cancel_state_clear_callback is not None:
                cancel_state_clear_callback(request.session_id)
    finally:
        logger.info(
            "[TTS] worker exit: thread=%s stop_event=%s",
            threading.current_thread().name,
            stop_event.is_set(),
        )
