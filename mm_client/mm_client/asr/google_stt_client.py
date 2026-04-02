from collections.abc import Iterable, Iterator
from queue import Queue
from threading import Event

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import speech

from asr.audio_input import MicrophoneAudioInput
from main.messages import RecognitionEvent, RecognitionEventType


class GoogleStreamingSttClient:
    """Google Cloud STT streaming adapter."""

    def __init__(self, sample_rate: int = 16000, language_code: str = "ja-JP") -> None:
        self.sample_rate = sample_rate
        self.language_code = language_code
        self.client = speech.SpeechClient()

    def stream(self, audio_chunks: Iterable[bytes]) -> Iterator[RecognitionEvent]:
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=self.language_code,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            enable_voice_activity_events=True,
        )

        requests = (
            speech.StreamingRecognizeRequest(audio_content=chunk)
            for chunk in audio_chunks
        )

        try:
            # pylint: disable=unexpected-keyword-arg
            responses = self.client.streaming_recognize(
                config=streaming_config,
                requests=requests,
            )
            # pylint: enable=unexpected-keyword-arg
        except (GoogleAPICallError, RetryError, OSError) as exc:
            yield RecognitionEvent(
                event_type=RecognitionEventType.ERROR,
                text=str(exc),
                raw=exc,
            )
            return

        for response in responses:
            if (
                response.speech_event_type
                == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_BEGIN
            ):
                yield RecognitionEvent(event_type=RecognitionEventType.SPEECH_STARTED, raw=response)
            elif (
                response.speech_event_type
                == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_END
            ):
                yield RecognitionEvent(event_type=RecognitionEventType.SPEECH_ENDED, raw=response)

            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            alt = result.alternatives[0]
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
        with MicrophoneAudioInput(sample_rate=sample_rate, chunk_ms=chunk_ms) as mic:
            for recognition_event in recognizer.stream(mic.chunks()):
                if stop_event.is_set():
                    break
                stt_event_queue.put(recognition_event)
    except (GoogleAPICallError, RetryError, OSError) as exc:
        stt_event_queue.put(
            RecognitionEvent(
                event_type=RecognitionEventType.ERROR,
                text=str(exc),
                raw=exc,
            )
        )
