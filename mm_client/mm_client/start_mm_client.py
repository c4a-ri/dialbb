import argparse
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from dialbb.util.logger import get_logger
from mm_client.asr.google_stt_client import run_stt_worker
from mm_client.main.dialbb_client import run_dialbb_worker
from mm_client.main.main_module import MultimodalMainModule
from mm_client.main.messages import (
    DialbbRequest,
    DialbbResponse,
    RecognitionEvent,
    TtsRequest,
    TtsResult,
)
from mm_client.tts.speech_synthesizer import run_tts_worker
import yaml


logger = get_logger(__name__)
DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent / "config" / "config.yml"


def _resolve_path(base_dir: Path, value: str | None) -> str | None:
    if not value:
        return None
    resolved = Path(value).expanduser()
    if not resolved.is_absolute():
        resolved = (base_dir / resolved).resolve()
    return str(resolved)


def _load_runtime_paths(
    config_file: Path,
) -> tuple[str | None, str | None]:
    config_data: dict = {}
    if config_file.exists():
        with config_file.open(encoding="utf-8") as fp:
            config_data = yaml.safe_load(fp) or {}
    else:
        logger.warning("[SYSTEM] 設定ファイルが見つかりません: %s", config_file)

    base_dir = config_file.parent
    stt_default = (config_data.get("stt") or {}).get("key_file")
    dialbb_default = (config_data.get("dialbb") or {}).get("config_file")

    stt_key_file = _resolve_path(base_dir, stt_default)
    dialbb_config = _resolve_path(base_dir, dialbb_default)
    return stt_key_file, dialbb_config


def _clear_queue(target_queue: queue.Queue) -> None:
    while True:
        try:
            target_queue.get_nowait()
        except queue.Empty:
            return


def _log_thread_shutdown_result(workers: list[threading.Thread], source: str) -> None:
    alive_workers = [worker.name for worker in workers if worker.is_alive()]
    if alive_workers:
        logger.warning("[%s] 未終了スレッドあり: %s", source, ", ".join(alive_workers))
    else:
        logger.info("[%s] 全ワーカースレッド終了を確認", source)

    running_threads = [thread.name for thread in threading.enumerate()]
    logger.info("[%s] 現在の生存スレッド: %s", source, ", ".join(running_threads))


class MultimodalGuiController:
    def __init__(
        self,
        root: tk.Tk,
        stop_event: threading.Event,
        conversation_active_event: threading.Event,
        stt_enabled_event: threading.Event,
        stt_event_queue: "queue.Queue[RecognitionEvent]",
        dialbb_request_queue: "queue.Queue[DialbbRequest]",
        dialbb_response_queue: "queue.Queue[DialbbResponse]",
        tts_request_queue: "queue.Queue[TtsRequest]",
        tts_result_queue: "queue.Queue[TtsResult]",
        workers: list[threading.Thread],
        chat_queue: "queue.Queue[tuple[str, str]]",
        error_queue: "queue.Queue[str]",
    ) -> None:
        self.root = root
        self.stop_event = stop_event
        self.conversation_active_event = conversation_active_event
        self.stt_enabled_event = stt_enabled_event
        self.stt_event_queue = stt_event_queue
        self.dialbb_request_queue = dialbb_request_queue
        self.dialbb_response_queue = dialbb_response_queue
        self.tts_request_queue = tts_request_queue
        self.tts_result_queue = tts_result_queue
        self.workers = workers
        self.chat_queue = chat_queue
        self.error_queue = error_queue
        self.is_closing = False
        self._ui_dialogue_active = False

        self.status_var = tk.StringVar(value="待機中")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close_gui)
        self.root.after(250, self._refresh_worker_state)
        self.root.after(100, self._poll_chat_queue)

    def _build_ui(self) -> None:
        self.root.title("DialBB Multimodal Client")
        self.root.geometry("520x380")

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # 上段: 対話ボタン（左）＋ステータス（右）を横並びで配置。
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(10, 10))

        self.start_button = ttk.Button(
            top_frame,
            text="対話開始",
            command=self.start_dialogue,
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))

        self.end_button = ttk.Button(
            top_frame,
            text="対話終了",
            command=self.end_dialogue,
            state=tk.DISABLED,
        )
        self.end_button.pack(side=tk.LEFT)

        status_label = ttk.Label(top_frame, textvariable=self.status_var, font=("Yu Gothic UI", 11))
        status_label.pack(side=tk.RIGHT)

        # 終了ボタンを先にpackしてチャット領域より優先的にスペースを確保する。
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))

        self.exit_button = ttk.Button(
            button_frame,
            text="終了",
            command=self.close_gui,
        )
        self.exit_button.pack(side=tk.RIGHT)

        # チャットウィンドウ：ユーザー発話とDialBB応答を表示するテキストエリア。
        chat_frame = ttk.LabelFrame(frame, text="対話履歴", padding=4)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.chat_text = tk.Text(
            chat_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Yu Gothic UI", 10),
            background="#1e1e1e",
            foreground="#d4d4d4",
            relief=tk.FLAT,
        )
        scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ユーザー発話用タグ（右寄せ、水色）。
        self.chat_text.tag_configure(
            "user",
            foreground="#4ec9b0",
            justify=tk.RIGHT,
            lmargin1=60,
            lmargin2=60,
        )
        # システム応答用タグ（左寄せ、黄色）。
        self.chat_text.tag_configure(
            "system",
            foreground="#dcdcaa",
            justify=tk.LEFT,
            rmargin=60,
        )
        # ラベル用タグ（グレー、小フォント）。
        self.chat_text.tag_configure(
            "label",
            foreground="#888888",
            font=("Yu Gothic UI", 8),
        )

    def _set_dialogue_ui_state(self, active: bool) -> None:
        self._ui_dialogue_active = active
        if active:
            self.start_button.configure(state=tk.DISABLED)
            self.end_button.configure(state=tk.NORMAL)
            self.status_var.set("対話中: システム発話後に音声入力開始")
            return
        self.start_button.configure(state=tk.NORMAL)
        self.end_button.configure(state=tk.DISABLED)
        self.status_var.set("待機中")

    def start_dialogue(self) -> None:
        if self.stop_event.is_set() or self.conversation_active_event.is_set():
            return

        # 前回対話の残キューを消してから開始要求を送る。
        _clear_queue(self.stt_event_queue)
        _clear_queue(self.dialbb_request_queue)
        _clear_queue(self.dialbb_response_queue)
        _clear_queue(self.tts_request_queue)
        _clear_queue(self.tts_result_queue)

        # チャットウィンドウをクリアする。
        self._clear_chat()

        self.conversation_active_event.set()
        self.stt_enabled_event.clear()
        self.dialbb_request_queue.put(
            DialbbRequest(session_id="", user_text="", is_initial=True)
        )
        logger.info("[GUI] 対話開始ボタン押下")
        self._set_dialogue_ui_state(active=True)

    def end_dialogue(self) -> None:
        if not self.conversation_active_event.is_set():
            return

        self.conversation_active_event.clear()
        self.stt_enabled_event.clear()

        # 対話停止時は待機復帰のため未処理メッセージを破棄する。
        _clear_queue(self.stt_event_queue)
        _clear_queue(self.dialbb_request_queue)
        _clear_queue(self.dialbb_response_queue)
        _clear_queue(self.tts_request_queue)
        _clear_queue(self.tts_result_queue)

        logger.info("[GUI] 対話終了ボタン押下")
        self._set_dialogue_ui_state(active=False)

    def close_gui(self) -> None:
        if self.is_closing:
            return
        self.is_closing = True

        logger.info("[GUI] 終了ボタン押下。停止処理を開始します。")
        self.conversation_active_event.clear()
        self.stt_enabled_event.clear()
        self.stop_event.set()

        for worker in self.workers:
            worker.join(timeout=3.0)

        _log_thread_shutdown_result(self.workers, source="GUI")
        if any(worker.is_alive() for worker in self.workers):
            self.status_var.set("未終了スレッドあり（ログ参照）")

        self.root.destroy()

    def _refresh_worker_state(self) -> None:
        if self.is_closing:
            return

        # ワーカーがまだ起動していない場合は監視をスキップする。
        started = [w for w in self.workers if w.ident is not None]
        dead_workers = [w.name for w in started if not w.is_alive()]
        if dead_workers:
            self.status_var.set(f"異常終了: {', '.join(dead_workers)}")
            logger.error("[GUI] ワーカー異常終了を検知: %s", ", ".join(dead_workers))
            # エラーキューにメッセージがあればポップアップで通知する。
            error_messages: list[str] = []
            while True:
                try:
                    error_messages.append(self.error_queue.get_nowait())
                except queue.Empty:
                    break
            if error_messages:
                messagebox.showerror(
                    "ワーカーエラー",
                    "\n\n".join(error_messages),
                    parent=self.root,
                )
            self.close_gui()
            return

        active = self.conversation_active_event.is_set()
        if active != self._ui_dialogue_active:
            self._ui_dialogue_active = active
            self._set_dialogue_ui_state(active=active)

        self.root.after(250, self._refresh_worker_state)

    def _clear_chat(self) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.configure(state=tk.DISABLED)

    def _append_chat(self, role: str, text: str) -> None:
        """role='user' or 'system' のメッセージをチャットウィンドウに追記する。"""
        label = "User" if role == "user" else "System"
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"{label}\n", "label")
        self.chat_text.insert(tk.END, f"{text}\n\n", role)
        self.chat_text.configure(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def _poll_chat_queue(self) -> None:
        if self.is_closing:
            return
        while True:
            try:
                role, text = self.chat_queue.get_nowait()
                self._append_chat(role, text)
            except queue.Empty:
                break
        self.root.after(100, self._poll_chat_queue)


def main() -> None:
    parser = argparse.ArgumentParser(description="DialBB multimodal client launcher")
    parser.add_argument(
        "config_file",
        nargs="?",
        default=str(DEFAULT_CONFIG_FILE),
        help="runtime config yaml path",
    )
    args = parser.parse_args()

    config_file = Path(args.config_file).expanduser().resolve()
    stt_key_file, dialbb_config = _load_runtime_paths(
        config_file=config_file,
    )

    if stt_key_file:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = stt_key_file
        logger.info("[SYSTEM] STTキー設定: %s", stt_key_file)
    else:
        logger.warning("[SYSTEM] STTキー未設定: config.yml を確認してください。")

    if dialbb_config:
        logger.info("[SYSTEM] DialBB設定: %s", dialbb_config)
    else:
        logger.warning("[SYSTEM] DialBB設定未指定: config.yml を確認してください。")

    logger.info("[SYSTEM] 起動: 4スレッド構成 (Main / STT / DialBB / TTS)")
    logger.info("[SYSTEM] GUIの『対話開始』で初回発話から対話を開始します。")

    # 全スレッドで共有する停止シグナル。
    stop_event = threading.Event()
    # 対話開始/終了の状態シグナル。
    conversation_active_event = threading.Event()
    # STT の受付可否シグナル（TTS再生中や待機中は OFF）。
    stt_enabled_event = threading.Event()

    # スレッド間通信キュー（STT -> Main -> DialBB/TTS）。
    stt_event_queue: "queue.Queue[RecognitionEvent]" = queue.Queue()
    dialbb_request_queue: "queue.Queue[DialbbRequest]" = queue.Queue()
    dialbb_response_queue: "queue.Queue[DialbbResponse]" = queue.Queue()
    tts_request_queue: "queue.Queue[TtsRequest]" = queue.Queue()
    tts_result_queue: "queue.Queue[TtsResult]" = queue.Queue()
    # GUIチャット表示用キュー (role: str, text: str) のタプルを受け取る。
    chat_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
    # ワーカーからGUIへのエラー通知キュー。
    error_queue: "queue.Queue[str]" = queue.Queue()
    # main_module から TTS ワーカーへの再生キャンセル通知キュー。
    tts_cancel_queue: "queue.Queue[str]" = queue.Queue()

    main_module = MultimodalMainModule()

    # 各ワーカーを daemon スレッドで起動する。
    workers = [
        # STTスレッド: マイク入力を音声認識し、RecognitionEventをMainへ渡す。
        threading.Thread(
            target=run_stt_worker,
            kwargs={
                "stt_event_queue": stt_event_queue,
                "stop_event": stop_event,
                "listening_enabled_event": stt_enabled_event,
                "sample_rate": 16000,
                "chunk_ms": 100,
                "language_code": "ja-JP",
            },
            name="stt-worker",
            daemon=False,
        ),
        # DialBBスレッド: Mainからの問い合わせを受け、応答文を生成してMainへ返す。
        threading.Thread(
            target=run_dialbb_worker,
            kwargs={
                "dialbb_request_queue": dialbb_request_queue,
                "dialbb_response_queue": dialbb_response_queue,
                "stop_event": stop_event,
                "config_file": dialbb_config,
                "error_queue": error_queue,
            },
            name="dialbb-worker",
            daemon=False,
        ),
        # TTSスレッド: Mainから受け取ったテキストを音声合成し、完了通知を返す。
        threading.Thread(
            target=run_tts_worker,
            kwargs={
                "tts_request_queue": tts_request_queue,
                "tts_result_queue": tts_result_queue,
                "stop_event": stop_event,
                "conversation_active_event": conversation_active_event,
                "tts_cancel_queue": tts_cancel_queue,
            },
            name="tts-worker",
            daemon=False,
        ),
        # Mainスレッド: 全キューを監視し、STT/DialBB/TTS間のメッセージを中継・制御する。
        threading.Thread(
            target=main_module.run,
            kwargs={
                "stt_event_queue": stt_event_queue,
                "dialbb_request_queue": dialbb_request_queue,
                "dialbb_response_queue": dialbb_response_queue,
                "tts_request_queue": tts_request_queue,
                "tts_result_queue": tts_result_queue,
                "conversation_active_event": conversation_active_event,
                "stt_enabled_event": stt_enabled_event,
                "stop_event": stop_event,
                "chat_queue": chat_queue,
                "tts_cancel_queue": tts_cancel_queue,
            },
            name="main-module-worker",
            daemon=False,
        ),
    ]

    root = tk.Tk()
    controller = MultimodalGuiController(
        root=root,
        stop_event=stop_event,
        conversation_active_event=conversation_active_event,
        stt_enabled_event=stt_enabled_event,
        stt_event_queue=stt_event_queue,
        dialbb_request_queue=dialbb_request_queue,
        dialbb_response_queue=dialbb_response_queue,
        tts_request_queue=tts_request_queue,
        tts_result_queue=tts_result_queue,
        workers=workers,
        chat_queue=chat_queue,
        error_queue=error_queue,
    )

    def _start_workers() -> None:
        for worker in workers:
            worker.start()
        logger.info("[SYSTEM] 全ワーカー起動完了")

    # GUI を先に描画してからワーカーを起動する。
    root.after(0, _start_workers)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("[SYSTEM] Ctrl+C を受信。終了処理を開始します。")
        stop_event.set()
        for worker in workers:
            worker.join(timeout=3.0)
        _log_thread_shutdown_result(workers, source="SYSTEM")

    logger.info("[SYSTEM] 停止しました。")


if __name__ == "__main__":
    main()
