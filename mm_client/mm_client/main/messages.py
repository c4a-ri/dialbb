from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RecognitionEventType(str, Enum):
    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    ERROR = "error"


@dataclass(slots=True)
class RecognitionEvent:
    event_type: RecognitionEventType
    text: str = ""
    confidence: float | None = None
    raw: Any = None
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class DialbbRequest:
    session_id: str
    user_text: str


@dataclass(slots=True)
class DialbbResponse:
    session_id: str
    system_text: str


@dataclass(slots=True)
class TtsRequest:
    session_id: str
    text: str


@dataclass(slots=True)
class TtsResult:
    session_id: str
    text: str
    completed: bool
