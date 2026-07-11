import threading
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
_AUDIO_ENCODING: texttospeech.AudioEncoding = cast(
    texttospeech.AudioEncoding,
    texttospeech.AudioEncoding.MP3,
)


def _synthesize_with_encoding(
    client: texttospeech.TextToSpeechClient,
    text: str,
    audio_encoding: texttospeech.AudioEncoding,
) -> bytes:
    """指定したエンコーディングで Google Cloud TTS 合成を行う。"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=_LANGUAGE_CODE,
        name=_VOICE_NAME,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=audio_encoding)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return response.audio_content


def _synthesize(client: texttospeech.TextToSpeechClient, text: str) -> bytes:
    """テキストを Google Cloud TTS で合成して既定形式のバイト列を返す。"""
    return _synthesize_with_encoding(client, text, _AUDIO_ENCODING)


def split_tts_segments(text: str) -> list[str]:
    """TTS 合成用にテキストを句読点単位で分割する。"""
    segments = [segment.strip() for segment in text.split("。") if segment.strip()]
    return [
        (segment + "。") if not segment.endswith(("。", "！", "？", "!", "?")) else segment
        for segment in segments
    ]


def run_tts_worker(
    tts_request_queue: "Queue[TtsRequest]",
    tts_result_queue: "Queue[TtsResult]",
    stop_event: Event,
    conversation_active_event: "Event | None" = None,
    tts_cancel_queue: "Queue[str] | None" = None,
    cancel_state_clear_callback: Callable[[str], None] | None = None,
    audio_send_callback: Callable[[int, int, bytes], None] | None = None,
) -> None:
    """Google Cloud TTS による音声合成ワーカースレッド。

    クライアント音声モードでは、TTS を句点単位で逐次合成し、
    audio_send_callback でクライアントへ音声データを渡す。
    """
    logger.info("[TTS] worker start: thread=%s", threading.current_thread().name)
    try:
        client = texttospeech.TextToSpeechClient()
        active_event = conversation_active_event or Event()
        if conversation_active_event is None:
            active_event.set()

        if audio_send_callback is None:
            logger.error("[TTS] audio_send_callback が未設定のため音声送信を行えません")
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

            logger.info("[TTS] TTS<-MAIN 合成要求受信")
            logger.debug("[TTS] request.text=%s", request.text)

            segments = split_tts_segments(request.text)
            total_segments = len(segments)

            completed = True
            for segment_index, segment in enumerate(segments, start=1):
                if stop_event.is_set() or not active_event.is_set():
                    logger.debug("[TTS] 中断: %s", segment)
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
                        logger.info("[TTS] cancel 受信: segment=%d/%d", segment_index, total_segments)
                        completed = False
                        break

                logger.debug("[TTS] 合成中: %s", segment)
                try:
                    audio_bytes = _synthesize(client, segment)
                except (GoogleAPICallError, RetryError, OSError):
                    logger.exception("[TTS] 合成エラー: %s", segment)
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
                        logger.info("[TTS] cancel 受信 (synth後): segment=%d/%d", segment_index, total_segments)
                        completed = False
                        break

                audio_send_callback(segment_index, total_segments, audio_bytes)

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
