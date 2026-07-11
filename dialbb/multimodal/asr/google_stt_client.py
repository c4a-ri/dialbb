from collections.abc import Iterable, Iterator
import threading
import time
from queue import Queue
from threading import Event
from typing import Any, cast

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import GoogleAuthError
from google.cloud import speech

from dialbb.util.logger import get_logger
from .audio_input import WebSocketAudioInput
from ..main.messages import RecognitionEvent, RecognitionEventType

logger = get_logger(__name__)


class GoogleStreamingSttClient:
    """Google Cloud STT streaming adapter."""

    def __init__(self, sample_rate: int = 16000, language_code: str = "ja-JP") -> None:
        self.sample_rate = sample_rate
        self.language_code = language_code
        # 認証情報は環境変数など ADC から解決される。
        self.client = speech.SpeechClient()

    def stream(self, audio_chunks: Iterable[bytes]) -> Iterator[RecognitionEvent]:
        # STT 設定（PCM16 / サンプリング周波数 / 言語）。
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=self.language_code,
        )

        # 逐次認識を有効化し、中間結果とVADイベントを受け取る。
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            enable_voice_activity_events=True,
        )

        def _requests() -> Iterator[speech.StreamingRecognizeRequest]:
            # マイクから渡された生PCMチャンクを逐次リクエスト化する。
            for chunk in audio_chunks:
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            # STT ストリーミングAPIを開始し、音声チャンク列から認識結果ストリームを取得する。
            responses = cast(Any, self.client).streaming_recognize(streaming_config, _requests())
        except (GoogleAPICallError, RetryError, OSError) as exc:
            # API 呼び出し失敗は ERROR イベントに変換して上位へ返す。
            yield RecognitionEvent(
                event_type=RecognitionEventType.ERROR,
                text=str(exc),
                raw=exc,
            )
            return

        for response in responses:
            # 音声区間イベント（発話開始/終了）を Main へ通知する。
            if (
                response.speech_event_type
                == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_BEGIN
            ):
                # 発話開始イベントを生成して返す
                yield RecognitionEvent(event_type=RecognitionEventType.SPEECH_STARTED, raw=response)
            elif (
                response.speech_event_type
                == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_END
            ):
                # 発話終了イベントを生成して返す
                yield RecognitionEvent(event_type=RecognitionEventType.SPEECH_ENDED, raw=response)

            if not response.results:
                # 結果がまだ無いイベントは次レスポンスへ。
                continue

            result = response.results[0]
            if not result.alternatives:
                # 候補が空のケースもスキップする。
                continue
            
            logger.debug("[STT] result.is_final=%s, alternatives=%s", result.is_final, result.alternatives)
            alt = result.alternatives[0]
            # 確定/中間の別をイベント型に変換して返す。
            evt_type = (
                RecognitionEventType.FINAL_TRANSCRIPT
                if result.is_final
                else RecognitionEventType.PARTIAL_TRANSCRIPT
            )
            yield RecognitionEvent(
                event_type=evt_type,
                text=alt.transcript,
                confidence=alt.confidence if result.is_final else None,
                raw=response,
            )


def run_stt_worker(
    stt_event_queue: "Queue[RecognitionEvent]",
    stop_event: Event,
    listening_enabled_event: Event | None = None,
    sample_rate: int = 16000,
    language_code: str = "ja-JP",
    audio_chunk_queue: "Queue[bytes | None] | None" = None,
) -> None:
    """Speech activity detection + STT worker thread.

    audio_chunk_queue が指定された場合は WebSocket 経由で受信した音声を STT に流す。
    未指定の場合は処理を開始しない。
    """
    logger.info(
        "[STT] worker start: thread=%s mode=%s",
        threading.current_thread().name,
        "websocket" if audio_chunk_queue is not None else "disabled",
    )
    try:
        try:
            recognizer = GoogleStreamingSttClient(
                sample_rate=sample_rate,
                language_code=language_code,
            )
        except (GoogleAPICallError, RetryError, GoogleAuthError, OSError) as exc:
            stt_event_queue.put(
                RecognitionEvent(
                    event_type=RecognitionEventType.ERROR,
                    text=str(exc),
                    raw=exc,
                )
            )
            return

        # --- WebSocket 音声モード（クライアントから音声チャンクを受信） ---
        if audio_chunk_queue is not None:
            import queue as _q
            while not stop_event.is_set():
                if listening_enabled_event and not listening_enabled_event.is_set():
                    time.sleep(0.1)
                    continue
                # 新セッション開始前にキューの古いデータを消去
                while not audio_chunk_queue.empty():
                    try:
                        audio_chunk_queue.get_nowait()
                    except _q.Empty:
                        break
                logger.info("[STT] WebSocket audio mode: waiting for audio chunks...")
                ws_audio = WebSocketAudioInput(audio_chunk_queue, listening_enabled_event, stop_event)
                try:
                    for recognition_event in recognizer.stream(ws_audio.chunks()):
                        if stop_event.is_set():
                            break
                        if listening_enabled_event and not listening_enabled_event.is_set():
                            break
                        stt_event_queue.put(recognition_event)
                except (GoogleAPICallError, RetryError, OSError) as exc:
                    if stop_event.is_set():
                        break
                    logger.warning("[STT] WS接続エラー(リトライ): %s", exc)
                    time.sleep(1.0)
                except (RuntimeError, ValueError, TypeError) as exc:
                    stt_event_queue.put(
                        RecognitionEvent(
                            event_type=RecognitionEventType.ERROR,
                            text=f"Unexpected STT error: {exc}",
                            raw=exc,
                        )
                    )
                    break
            return
    finally:
        logger.info(
            "[STT] worker exit: thread=%s stop_event=%s",
            threading.current_thread().name,
            stop_event.is_set(),
        )
