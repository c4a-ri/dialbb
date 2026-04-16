from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RecognitionEventType(str, Enum):
    """STT から Main へ渡す認識イベント種別。"""

    # 発話区間の開始を検知した通知。
    SPEECH_STARTED = "speech_started"
    # 発話区間の終了を検知した通知。
    SPEECH_ENDED = "speech_ended"
    # 認識途中の中間テキスト。
    PARTIAL_TRANSCRIPT = "partial_transcript"
    # 認識が確定した最終テキスト。
    FINAL_TRANSCRIPT = "final_transcript"
    # 認識処理中のエラー通知。
    ERROR = "error"


@dataclass(slots=True)
class RecognitionEvent:
    """STT スレッドから Main スレッドへ渡すイベント本体。"""

    # イベント種別（開始/終了/中間/確定/エラー）。
    event_type: RecognitionEventType
    # 認識テキスト（中間/確定/エラー文で利用）。
    text: str = ""
    # 最終認識時のみ設定される信頼度。
    confidence: float | None = None
    # STT SDK の元レスポンスや例外オブジェクト。
    raw: Any = None
    # イベント生成時刻。
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class DialbbRequest:
    """Main から DialBB へ送る問い合わせメッセージ。"""

    session_id: str
    user_text: str
    # True の場合は対話開始要求（initial=True）として扱う。
    is_initial: bool = False


@dataclass(slots=True)
class DialbbResponse:
    """DialBB から Main へ返す応答メッセージ。"""

    session_id: str
    system_text: str


@dataclass(slots=True)
class TtsRequest:
    """Main から TTS へ送る音声合成要求。"""

    session_id: str
    text: str


@dataclass(slots=True)
class TtsResult:
    """TTS から Main へ返す合成結果通知。"""

    session_id: str
    text: str
    # True の場合は当該テキストの合成処理完了を表す。
    completed: bool
