import io
from queue import Empty, Queue
from threading import Event

import pygame
from google.cloud import texttospeech

from dialbb.util.logger import get_logger
from mm_client.main.messages import TtsRequest, TtsResult


logger = get_logger(__name__)

# Google Cloud TTS の音声設定。
_LANGUAGE_CODE = "ja-JP"
_VOICE_NAME = "ja-JP-Neural2-B"
_AUDIO_ENCODING = texttospeech.AudioEncoding.MP3

# pygame mixer の初期化（モジュールロード時に一度だけ実行）。
pygame.mixer.init()


def _synthesize(client: texttospeech.TextToSpeechClient, text: str) -> bytes:
    """テキストを Google Cloud TTS で合成して MP3 バイト列を返す。"""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=_LANGUAGE_CODE,
        name=_VOICE_NAME,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=_AUDIO_ENCODING)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return response.audio_content


def _play_audio(
    audio_bytes: bytes,
    stop_event: Event,
    conversation_active_event: Event,
    cancel_queue: "Queue | None" = None,
) -> bool:
    """MP3 バイト列を pygame で再生する。

    Returns:
        True: 最後まで再生完了。
        False: stop_event / conversation_active_event / cancel_queue により中断。
    """
    buf = io.BytesIO(audio_bytes)
    pygame.mixer.music.load(buf, "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if stop_event.is_set() or not conversation_active_event.is_set():
            pygame.mixer.music.stop()
            return False
        if cancel_queue is not None:
            try:
                cancel_queue.get_nowait()
                logger.info("[TTS] キャンセルキュー受信: 再生中断")
                pygame.mixer.music.stop()
                return False
            except Exception:
                pass
        pygame.time.wait(50)
    return True


def run_tts_worker(
    tts_request_queue: "Queue[TtsRequest]",
    tts_result_queue: "Queue[TtsResult]",
    stop_event: Event,
    conversation_active_event: "Event | None" = None,
    tts_cancel_queue: "Queue | None" = None,
) -> None:
    """Google Cloud TTS + pygame による音声合成・再生ワーカースレッド。

    テキストを句点「。」で分割して逐次合成・再生し、
    stop_event / conversation_active_event / tts_cancel_queue で再生を中断できる。
    """
    client = texttospeech.TextToSpeechClient()
    # conversation_active_event が渡されない場合は常に active とみなす。
    active_event = conversation_active_event or Event()
    if conversation_active_event is None:
        active_event.set()

    while not stop_event.is_set():
        try:
            request = tts_request_queue.get(timeout=0.1)
        except Empty:
            continue

        logger.info("[TTS] 合成要求受信: %s", request.text)

        # 句点で分割し、空セグメントを除去する。
        segments = [s.strip() for s in request.text.split("。") if s.strip()]
        # 末尾が「。」で終わっていた場合は再度「。」を付け直す。
        segments = [
            (seg + "。") if not seg.endswith(("。", "！", "？", "!", "?")) else seg
            for seg in segments
        ]

        completed = True
        for segment in segments:
            if stop_event.is_set() or not active_event.is_set():
                logger.info("[TTS] 中断: %s", segment)
                completed = False
                break

            logger.info("[TTS] 合成中: %s", segment)
            try:
                audio_bytes = _synthesize(client, segment)
            except Exception:
                logger.exception("[TTS] 合成エラー: %s", segment)
                completed = False
                break

            finished = _play_audio(audio_bytes, stop_event, active_event, tts_cancel_queue)
            if not finished:
                logger.info("[TTS] 再生中断: %s", segment)
                completed = False
                break

        tts_result_queue.put(
            TtsResult(
                session_id=request.session_id,
                text=request.text,
                completed=completed,
            )
        )
        if completed:
            logger.info("[TTS] 合成・再生完了: %s", request.text)
