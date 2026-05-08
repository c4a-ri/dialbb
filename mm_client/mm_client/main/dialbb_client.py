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

    logger.info("[Dialbb] DialogueProcessor 初期化")
    logger.debug("[Dialbb] config=%s", resolved_config)
    captured = io.StringIO()
    try:
        # stdout を横取りして初期化エラーメッセージを捕捉する。
        with redirect_stdout(captured):
            dialogue_processor = DialogueProcessor(resolved_config)
    except (Exception, SystemExit) as exc:
        output = captured.getvalue().strip()
        # dialbb は sys.exit()（SystemExit）で終了するため stdout に出力されたメッセージを優先する。
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
    # 初回セッション ID は引数で差し込める（テスト用）。通常は None でよい。
    active_session_id = (initial_session_id or "").strip() or None

    while not stop_event.is_set():
        try:
            # Main からの問い合わせを待ち受ける。
            request = dialbb_request_queue.get(timeout=0.1)
        except Empty:
            continue

        # ----------------------------------------------------------------
        # 対話開始要求（is_initial=True）の処理
        # ----------------------------------------------------------------
        if request.is_initial:
            logger.info("[Dialbb] DialBB<-MAIN 初期化要求受信")
            # DialBB に initial=True でリクエストし、新規 session_id を取得する。
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

            # 最初のシステム発話テキストを Main へ返す。
            init_text = str(init_response.get("system_utterance", "")).strip()
            is_final = bool(init_response.get("final", False))
            dialbb_response_queue.put(
                DialbbResponse(
                    session_id=active_session_id,
                    system_text=init_text,
                    is_final=is_final,
                )
            )
            logger.info("[Dialbb] DialBB->MAIN 初回応答送信")
            if is_final:
                logger.debug("[Dialbb] 初回応答が最終応答です。")
            if not init_text:
                logger.debug("[Dialbb] 初回応答が空のため、発話せずユーザ発話待ちで継続します.")
            continue

        # ----------------------------------------------------------------
        # 通常の発話リクエストの処理
        # ----------------------------------------------------------------
        # 対話が未開始の状態で来たリクエストは無視する。
        if not active_session_id:
            logger.warning("[Dialbb] 未開始状態で通常リクエストを受信したため破棄します。")
            continue

        logger.info("[Dialbb] DialBB<-MAIN 発話要求受信")
        logger.debug("[Dialbb] user_text=%s", request.user_text)

        # 必須フィールドを入れてリクエスト辞書を構築する。
        dialbb_request = {
            "session_id": active_session_id,
            "user_id": user_id,
            "user_utterance": request.user_text,
        }
        # aux_data があればマージする（例： barge_in=True）。
        if request.aux_data:
            dialbb_request.update(request.aux_data)
            logger.debug("[Dialbb] aux_data=%s", request.aux_data)
        # DialBB に問い合わせて応答を得る。
        dialbb_response = dialogue_processor.process(dialbb_request)
        # レスポンスから session_id と発話テキストを取り出す。
        active_session_id = str(dialbb_response.get("session_id", active_session_id))
        system_text = str(dialbb_response.get("system_utterance", "")).strip()
        is_final = bool(dialbb_response.get("final", False))
        if not system_text:
            # 応答が空の場合はフォールバック文言で補完する。
            logger.warning("[Dialbb] system_utterance が空のためフォールバック文言を返します。")
            system_text = "すみません、うまく応答を生成できませんでした。"

        # 生成した応答文を Main へ返す。
        dialbb_response_queue.put(
            DialbbResponse(
                session_id=active_session_id,
                system_text=system_text,
                is_final=is_final,
            )
        )
        if is_final:
            logger.info("[Dialbb] DialBB->MAIN 応答送信（最終応答）")
        else:
            logger.info("[Dialbb] DialBB->MAIN 応答送信")


def _build_initial_request(user_id: str) -> dict[str, Any]:
    # 対話開始時は新規セッションを作るため user_id のみ渡す。
    return {"user_id": user_id}
