import io
import os
import sys
from contextlib import redirect_stdout
from queue import Empty, Queue
from threading import Event
from typing import Any

from dialbb.util.logger import get_logger
from dialbb.main import DialogueProcessor
from mm_client.main.messages import DialbbRequest, DialbbResponse


logger = get_logger(__name__)
DEFAULT_DIALBB_USER_ID = "mm-client"


def run_dialbb_worker(
    dialbb_request_queue: "Queue[DialbbRequest]",
    dialbb_response_queue: "Queue[DialbbResponse]",
    stop_event: Event,
    initial_session_id: str | None = None,
    config_file: str | None = None,
    user_id: str = DEFAULT_DIALBB_USER_ID,
    error_queue: "Queue[str] | None" = None,
) -> None:
    """DialBB client worker thread.
    """
    resolved_config = config_file or os.getenv("DIALBB_CONFIG")
    if not resolved_config:
        msg = "DIALBB_CONFIG が未設定です。config_file または環境変数を設定してください。"
        if error_queue is not None:
            error_queue.put(msg)
        raise ValueError(msg)

    logger.info("[Dialbb] DialogueProcessor 初期化: %s", resolved_config)
    captured = io.StringIO()
    try:
        with redirect_stdout(captured):
            dialogue_processor = DialogueProcessor(resolved_config)
    except BaseException as exc:
        output = captured.getvalue().strip()
        # dialbb は sys.exit() で終了するため stdout に出力されたメッセージを優先する。
        # "Encountered an error" を含む行だけ抽出してユーザへ見せる。
        error_lines = [
            line.strip()
            for line in output.splitlines()
            if "encountered an error" in line.lower() or "error" in line.lower()
        ]
        msg = "\n".join(error_lines) if error_lines else (output or str(exc) or type(exc).__name__)
        logger.error("[Dialbb] 初期化エラー: %s", msg)
        if error_queue is not None:
            error_queue.put(msg)
        sys.exit(1)
    active_session_id = (initial_session_id or "").strip() or None

    while not stop_event.is_set():
        try:
            # Main からの問い合わせを待ち受ける。
            request = dialbb_request_queue.get(timeout=0.1)
        except Empty:
            continue

        if request.is_initial:
            logger.info("[Dialbb] 対話開始要求を受信")
            init_response = dialogue_processor.process(
                _build_initial_request(user_id=user_id),
                initial=True,
            )
            init_session_id = init_response.get("session_id")
            if not init_session_id:
                raise ValueError("DialBB 初回応答に session_id がありません。")
            active_session_id = str(init_session_id).strip()
            if not active_session_id:
                raise ValueError("DialBB 初回応答の session_id が空です。")

            init_text = str(init_response.get("system_utterance", "")).strip()
            dialbb_response_queue.put(
                DialbbResponse(
                    session_id=active_session_id,
                    system_text=init_text,
                )
            )
            if not init_text:
                logger.info("[Dialbb] 初回応答が空のため、発話せずユーザ発話待ちで継続します。")
            continue

        if not active_session_id:
            logger.warning("[Dialbb] 未開始状態で通常リクエストを受信したため破棄します。")
            continue

        logger.info("[Dialbb] リクエスト受信: %s", request.user_text)

        dialbb_request = {
            "session_id": active_session_id,
            "user_id": user_id,
            "user_utterance": request.user_text,
        }
        dialbb_response = dialogue_processor.process(dialbb_request)
        active_session_id = str(dialbb_response.get("session_id", active_session_id))
        system_text = str(dialbb_response.get("system_utterance", "")).strip()
        if not system_text:
            logger.warning("[Dialbb] system_utterance が空のためフォールバック文言を返します。")
            system_text = "すみません、うまく応答を生成できませんでした。"

        dialbb_response_queue.put(
            DialbbResponse(session_id=active_session_id, system_text=system_text)
        )


def _build_initial_request(user_id: str) -> dict[str, Any]:
    # 対話開始時は新規セッションを作るため user_id のみ渡す。
    return {"user_id": user_id}
