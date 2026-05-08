import time
from queue import Empty, Queue
from threading import Event
from typing import Optional

from dialbb.util.logger import get_logger
from mm_client.main.messages import (
    DialbbRequest,
    DialbbResponse,
    RecognitionEvent,
    RecognitionEventType,
    TtsRequest,
    TtsResult,
)


logger = get_logger(__name__)


class MultimodalMainModule:
    """Main module worker that mediates modules via queues."""

    def __init__(self) -> None:
        self.session_id: str = ""
        # --- 状態変数 ---
        # ユーザが発話中（音声区間内）かどうか。
        self.user_speaking: bool = False
        # システム発話終了後のユーザ発話待ち状態かどうか。
        self.user_waiting: bool = False
        # システムが発話中かどうか。
        self.system_speaking: bool = False
        # ユーザ発話待ち開始時刻（time.monotonic() 基準）。None = 未計測。
        self.user_wait_start_time: Optional[float] = None
        # バージインキャンセルを送信済みかどうか（PARTIAL 連続受信で重複送信を防ぐ）。
        self._barge_in_sent: bool = False
        # DialBB が最終応答を返したかどうか（対話終了フラグ）。
        self.is_final_response: bool = False

    def _reset_state(self) -> None:
        """対話開始・終了時に状態変数をリセットする。"""
        self.session_id = ""
        self.user_speaking = False
        self.user_waiting = False
        self.system_speaking = False
        self.user_wait_start_time = None
        self._barge_in_sent = False
        self.is_final_response = False

    @staticmethod
    def _drain(q: "Queue") -> None:
        """キューに残留するメッセージを全て破棄する。"""
        while not q.empty():
            try:
                q.get_nowait()
            except Empty:
                break

    @staticmethod
    def _publish_status(status_queue: Optional[Queue], message: str) -> None:
        if status_queue is not None:
            status_queue.put(message)

    def run(
        self,
        stt_event_queue: "Queue[RecognitionEvent]",
        dialbb_request_queue: "Queue[DialbbRequest]",
        dialbb_response_queue: "Queue[DialbbResponse]",
        tts_request_queue: "Queue[TtsRequest]",
        tts_result_queue: "Queue[TtsResult]",
        conversation_active_event: Event,
        stt_enabled_event: Event,
        stop_event: Event,
        gui_command_queue: "Queue[str]",
        chat_queue: Optional[Queue] = None,
        status_queue: Optional[Queue] = None,
        tts_cancel_queue: Optional[Queue] = None,
        loop_period: float = 0.1,
        max_user_wait_time: float = 30.0,
    ) -> None:
        # stop_event がセットされるまでループを回し続ける。
        while not stop_event.is_set():
            # ループ周期計算のために開始時刻を記録する。
            loop_start = time.monotonic()

            # ----------------------------------------------------------------
            # 1. GUIコマンドを処理する（"start" / "end"）
            # ----------------------------------------------------------------
            try:
                cmd = gui_command_queue.get_nowait()
                if cmd == "start":
                    logger.info("[MAIN] GUI->MAIN start コマンド受信")
                    self._publish_status(status_queue, "対話初期化中")
                    # 状態変数を初期値に戻す。
                    self._reset_state()
                    # 全キューの残留メッセージを破棄してクリーンな状態で開始する。
                    self._drain(stt_event_queue)
                    self._drain(dialbb_request_queue)
                    self._drain(dialbb_response_queue)
                    self._drain(tts_result_queue)
                    if tts_cancel_queue is not None:
                        self._drain(tts_cancel_queue)
                    # 対話アクティブ状態・STT有効状態にする。
                    conversation_active_event.set()
                    stt_enabled_event.set()
                    # DialBB に初期化リクエストを送り、最初のシステム発話を得る。
                    logger.info("[MAIN] MAIN->DialBB 初期化要求送信")
                    self._publish_status(status_queue, "システム応答待ち")
                    dialbb_request_queue.put(
                        DialbbRequest(session_id="", user_text="", is_initial=True)
                    )
                elif cmd == "end":
                    logger.info("[MAIN] GUI->MAIN end コマンド受信")
                    self._publish_status(status_queue, "待機中")
                    # 再生中の TTS を即時中断する。
                    if tts_cancel_queue is not None:
                        tts_cancel_queue.put("cancel")
                    # STT・対話アクティブを無効化する。
                    stt_enabled_event.clear()
                    conversation_active_event.clear()
                    # 状態変数をリセットする。
                    self._reset_state()
                    # 未処理の残留メッセージを破棄する。
                    self._drain(stt_event_queue)
                    self._drain(dialbb_request_queue)
                    self._drain(dialbb_response_queue)
                    self._drain(tts_request_queue)
                    self._drain(tts_result_queue)
            except Empty:
                pass

            # ----------------------------------------------------------------
            # 2. STTイベントを処理する（stt_event_queue をドレイン）
            # ----------------------------------------------------------------
            # キューに溜まったイベントをこのループ周期で全て消化する。
            while True:
                try:
                    stt_event = stt_event_queue.get_nowait()
                except Empty:
                    break

                # 対話が非アクティブな場合はイベントを読み捨てる。
                if not conversation_active_event.is_set():
                    continue

                if stt_event.event_type == RecognitionEventType.SPEECH_STARTED:
                    # 音声区間開始：ユーザ発話中フラグを立て、発話待ち状態を解除する。
                    logger.debug("[MAIN] 音声区間開始")
                    self.user_speaking = True
                    self._publish_status(status_queue, "音声認識中")
                    # user_waiting は維持して、timeout 判定側で user_speaking 中を除外する。
                    # これにより FINAL 未到達時でも待ち状態が失われない。

                elif stt_event.event_type == RecognitionEventType.SPEECH_ENDED:
                    # 音声区間終了：FINAL が来ないケースでも待機判定へ戻せるよう false に戻す。
                    # FINAL_TRANSCRIPT 側でも false を再設定するため、順序が前後しても安全。
                    logger.debug("[MAIN] 音声区間終了")
                    self.user_speaking = False

                elif stt_event.event_type == RecognitionEventType.PARTIAL_TRANSCRIPT:
                    logger.debug("[MAIN] 認識中... %s", stt_event.text)
                    self._publish_status(status_queue, "音声認識中")
                    # システム発話中に部分認識が来たら即キャンセルする（早期バージイン）。
                    # ただし最終応答再生中はバージインしない。
                    # 複数回届くが tts_cancel_queue は1回送れば十分なので _barge_in_sent フラグで制御。
                    if (
                        self.system_speaking
                        and not self.is_final_response
                        and tts_cancel_queue is not None
                        and not self._barge_in_sent
                    ):
                        tts_cancel_queue.put("cancel")
                        self._barge_in_sent = True
                        logger.info("[MAIN] MAIN->TTS cancel 送信（barge-in）")

                elif stt_event.event_type == RecognitionEventType.FINAL_TRANSCRIPT:
                    text = stt_event.text.strip()
                    logger.info("[MAIN] STT->MAIN final: %s", text)
                    self._publish_status(status_queue, "応答生成中")
                    # 確定結果受信でユーザ発話中フラグを解除する。
                    self.user_speaking = False
                    # ユーザ発話処理中は待機タイムアウトを停止する。
                    self.user_waiting = False
                    self.user_wait_start_time = None
                    # システム発話中にユーザが割り込んだ場合は barge_in フラグを付ける。
                    # ただし最終応答再生中はバージイン判定を行わない。
                    aux_data: dict = (
                        {"barge_in": True} if (self.system_speaking and not self.is_final_response) else {}
                    )
                    # ユーザ発話テキストを DialBB へ送る。
                    logger.info("[MAIN] MAIN->DialBB 発話要求送信")
                    dialbb_request_queue.put(
                        DialbbRequest(
                            session_id=self.session_id,
                            user_text=text,
                            aux_data=aux_data,
                        )
                    )
                    if aux_data:
                        logger.debug("[MAIN] DialBB aux_data=%s", aux_data)
                    # PARTIAL でキャンセル済みでも念のため再送する（冪等）。
                    # ただし最終応答再生中はキャンセルを送らない。
                    if tts_cancel_queue is not None and not self.is_final_response:
                        tts_cancel_queue.put("cancel")
                        logger.debug("[MAIN] MAIN->TTS cancel 冪等送信")
                    # チャット表示用キューにも送る。
                    if chat_queue is not None:
                        chat_queue.put(("user", text))

                elif stt_event.event_type == RecognitionEventType.ERROR:
                    logger.error("[MAIN][STT ERROR] %s", stt_event.text)
                    self._publish_status(status_queue, "音声認識エラー")

            # ----------------------------------------------------------------
            # 3. DialBBからのシステム発話テキストを処理する
            # ----------------------------------------------------------------
            # DialBB 応答キューをドレインし、テキストを TTS へ転送する。
            while True:
                try:
                    dialbb_response = dialbb_response_queue.get_nowait()
                except Empty:
                    break

                logger.info("[MAIN] MAIN<-DialBB 応答受信")
                logger.debug("[MAIN] DialBB応答: %s", dialbb_response.system_text)
                # DialBB が払い出した session_id を以降のリクエストに使う。
                self.session_id = dialbb_response.session_id
                # 最終応答フラグをセット（これ以降は新しい入力を受け付けない）。
                if dialbb_response.is_final:
                    self.is_final_response = True
                    logger.info("[MAIN] DialBB 最終応答を受信（対話終了予定）")

                if not conversation_active_event.is_set():
                    logger.debug("[MAIN] 対話停止中のため DialBB 応答を破棄します。")
                    continue

                if self.user_speaking and self.system_speaking:
                    # バージイン中（ユーザ発話中かつシステム発話中）はスキップする。
                    # FINAL_TRANSCRIPT後にbarge_in付きリクエストが送られ直す。
                    logger.debug("[MAIN] バージイン中のため DialBB 応答を無視します。")
                    continue

                system_text = dialbb_response.system_text.strip()
                if not system_text:
                    # 空応答はユーザ発話待ちへ遷移する。
                    logger.info("[MAIN] DialBB空応答: ユーザ発話待ちへ遷移")
                    self._publish_status(status_queue, "音声入力待ち")
                    self.user_waiting = True
                    self.user_wait_start_time = time.monotonic()
                    # 最終応答の場合は新しい入力を受け付けない。
                    if not self.is_final_response:
                        stt_enabled_event.set()
                    continue

                # システム発話中フラグを立て、TTS にテキストを送る。
                self.system_speaking = True
                # チャット表示用キューにも送る。
                if chat_queue is not None:
                    chat_queue.put(("system", system_text))
                logger.info("[MAIN] MAIN->TTS 合成要求送信")
                self._publish_status(status_queue, "音声合成中")
                tts_request_queue.put(
                    TtsRequest(session_id=self.session_id, text=system_text)
                )
                # 最終応答の場合は、TTS 再生中の新しいユーザー入力を禁止する。
                if self.is_final_response:
                    logger.debug("[MAIN] 最終応答再生中: 新規 STT 入力を無効化")
                    stt_enabled_event.clear()

            # ----------------------------------------------------------------
            # 4. システム発話終了情報を処理する
            # ----------------------------------------------------------------
            # TTS ワーカーから完了・中断の通知を受け取り、状態を更新する。
            while True:
                try:
                    tts_result = tts_result_queue.get_nowait()
                except Empty:
                    break

                logger.info("[MAIN] MAIN<-TTS 結果受信")
                if tts_result.completed:
                    # 正常完了の場合の遷移を判定。
                    logger.info("[MAIN] システム発話終了")
                    self.system_speaking = False
                    self._barge_in_sent = False

                    if self.is_final_response:
                        # 最終応答の再生が完了 → 対話終了に遷移する。
                        logger.info("[MAIN] 最終応答の再生完了：対話終了に遷移")
                        self._publish_status(status_queue, "対話終了")
                        self._reset_state()
                        conversation_active_event.clear()
                    else:
                        # 通常応答 → ユーザ発話待ち状態へ遷移する。
                        self._publish_status(status_queue, "音声入力待ち")
                        self.user_waiting = True
                        self.user_wait_start_time = time.monotonic()
                        stt_enabled_event.set()
                else:
                    # バージインまたはエラーによる中断：フラグだけリセットする。
                    logger.info("[MAIN] システム発話中断またはエラー")
                    logger.debug("[MAIN] TTS結果詳細: %s", tts_result.text)
                    if conversation_active_event.is_set():
                        self._publish_status(status_queue, "音声入力待ち")
                    self.system_speaking = False
                    self._barge_in_sent = False

            # ----------------------------------------------------------------
            # 5. ユーザ発話待ちタイムアウト → "user_silence" を DialBB へ送る
            # ----------------------------------------------------------------
            if (
                self.user_waiting
                and self.user_wait_start_time is not None
                and conversation_active_event.is_set()
                and not self.user_speaking
            ):
                elapsed_wait = time.monotonic() - self.user_wait_start_time
                if elapsed_wait > max_user_wait_time:
                    logger.info("[MAIN] MAIN->DialBB user_silence 送信")
                    logger.debug("[MAIN] ユーザ発話待ちタイムアウト %.1f 秒", elapsed_wait)
                    self._publish_status(status_queue, "応答生成中（無音タイムアウト）")
                    dialbb_request_queue.put(
                        DialbbRequest(session_id=self.session_id, user_text="user_silence")
                    )
                    # 再送防止のためタイマーをリセットする。
                    self.user_wait_start_time = time.monotonic()

            # ----------------------------------------------------------------
            # 6. ループ周期タイミング制御
            # ----------------------------------------------------------------
            # 処理時間を差し引いた残り時間だけスリープし、周期を一定に保つ。
            elapsed = time.monotonic() - loop_start
            t = loop_period - elapsed
            if t > 0:
                time.sleep(t)
