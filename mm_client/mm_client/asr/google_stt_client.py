from collections.abc import Iterable, Iterator
import time
from queue import Queue
from threading import Event

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import GoogleAuthError
from google.cloud import speech

from dialbb.util.logger import get_logger
from mm_client.asr.audio_input import MicrophoneAudioInput
from mm_client.main.messages import RecognitionEvent, RecognitionEventType

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

        requests = (
            # マイクから渡された生PCMチャンクを逐次リクエスト化する。
            speech.StreamingRecognizeRequest(audio_content=chunk)
            for chunk in audio_chunks
        )

        try:
            # pylint: disable=unexpected-keyword-arg
            # STT ストリーミングAPIを開始し、音声チャンク列から認識結果ストリームを取得する。
            responses = self.client.streaming_recognize(
                config=streaming_config,
                requests=requests,
            )
            # pylint: enable=unexpected-keyword-arg
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
    chunk_ms: int = 100,
    language_code: str = "ja-JP",
) -> None:
    """Speech activity detection + STT worker thread."""
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

    while not stop_event.is_set():
        if listening_enabled_event and not listening_enabled_event.is_set():
            # 音声受付OFF時はマイクを開かず待機する。
            time.sleep(0.1)
            continue

        try:
            # マイク入力を逐次 chunk 化して STT に流し込む。
            with MicrophoneAudioInput(sample_rate=sample_rate, chunk_ms=chunk_ms) as mic:
                for recognition_event in recognizer.stream(mic.chunks()):
                    if stop_event.is_set():
                        # 停止シグナルを受けたら即座にループを抜ける。
                        break
                    if listening_enabled_event and not listening_enabled_event.is_set():
                        # 音声受付OFFへ切り替わったためマイクを閉じて待機へ戻る。
                        break
                    stt_event_queue.put(recognition_event)
        except (GoogleAPICallError, RetryError, OSError) as exc:
            # 503 など一時的な接続エラーはログ出力のみでリトライする。
            if stop_event.is_set():
                break
            logger.warning("[STT] 接続エラー(リトライ): %s", exc)
            time.sleep(1.0)
        except Exception as exc:  # noqa: BLE001
            # 想定外例外も握りつぶさず可視化する。
            stt_event_queue.put(
                RecognitionEvent(
                    event_type=RecognitionEventType.ERROR,
                    text=f"Unexpected STT error: {exc}",
                    raw=exc,
                )
            )
            break
