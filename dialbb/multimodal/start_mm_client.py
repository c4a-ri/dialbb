import argparse
import os
import platform
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from pathlib import Path

import yaml
from dialbb.util.logger import get_logger
from .core import DialogueEvent
from .engine import DialogueEngineManager, SessionConfig


logger = get_logger(__name__)
DEFAULT_CONFIG_FILE = Path.cwd() / "config" / "mm_client_config.yml"
MISSING_CONFIG_GUIDANCE = (
    "Configファイルが見つかりません、コマンド引数で指定するかconfig/mm_client_config.yml"
    "があるディレクトリでコマンドを実行してください"
)

# OS ごとの日本語フォント候補。
_FONT_CANDIDATES: dict[str, list[str]] = {
    "Windows": ["Yu Gothic UI", "Meiryo UI", "MS Gothic"],
    "Darwin": ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "Osaka"],
    "Linux": ["Noto Sans CJK JP", "IPAexGothic", "VL Gothic"],
}


def _resolve_path(base_dir: Path, value: str | None) -> str | None:
    if not value:
        return None
    resolved = Path(value).expanduser()
    if not resolved.is_absolute():
        resolved = (base_dir / resolved).resolve()
    return str(resolved)


def _pick_font(size: int) -> tuple[str, int]:
    """実行環境に応じた日本語フォントを選んで (family, size) を返す。
    利用可能なフォントが見つからない場合は Tk デフォルトを使う。
    """
    available = set(tkfont.families())
    candidates = _FONT_CANDIDATES.get(platform.system(), [])
    for name in candidates:
        if name in available:
            return (name, size)
    # フォールバック: Tk デフォルトフォントのファミリを流用する。
    default_family = tkfont.nametofont("TkDefaultFont").cget("family")
    return (default_family, size)


def _load_runtime_paths(
    config_file: Path,
) -> tuple[str | None, str | None, float, float, float]:
    # YAML 設定ファイルを読み込む（存在しない場合は空辞書で継続）。
    config_data: dict = {}
    if config_file.exists():
        with config_file.open(encoding="utf-8") as fp:
            config_data = yaml.safe_load(fp) or {}
    else:
        logger.warning("[SYSTEM] 設定ファイルが見つかりません: %s", config_file)

    base_dir = config_file.parent
    # STT 認証キーファイルと DialBB 設定ファイルのパスを解決する。
    stt_default = (config_data.get("stt") or {}).get("key_file")
    dialbb_default = (config_data.get("dialbb") or {}).get("config_file")

    stt_key_file = _resolve_path(base_dir, stt_default)
    dialbb_config = _resolve_path(base_dir, dialbb_default)

    # メインループの周期とユーザ発話待ちタイムアウトを読む。
    main_cfg = config_data.get("main") or {}
    loop_period = float(main_cfg.get("loop_period", 0.1))
    max_user_wait_time = float(main_cfg.get("max_user_wait_time", 30.0))

    # マイクゲイン値を読む（1.0=原音、小さくするとマイクの感度を下げられる）。
    stt_cfg = config_data.get("stt") or {}
    mic_gain = float(stt_cfg.get("mic_gain", 1.0))

    return stt_key_file, dialbb_config, loop_period, max_user_wait_time, mic_gain


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
        engine_manager: DialogueEngineManager,
        session_id: str,
    ) -> None:
        self.root = root
        self.engine_manager = engine_manager
        self.session_id = session_id
        self.is_closing = False
        self._ui_dialogue_active = False
        # イベントキュー（エンジンからのイベントを UI へ伝達）
        self.event_queue: "queue.Queue[DialogueEvent]" = queue.Queue()

        self.status_var = tk.StringVar(value="待機中")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close_gui)
        self.root.after(250, self._refresh_engine_state)
        self.root.after(100, self._poll_engine_events)

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

        status_label = ttk.Label(top_frame, textvariable=self.status_var, font=_pick_font(11))
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
            font=_pick_font(10),
            background="#212121",
            foreground="#ffffff",
            relief=tk.FLAT,
        )
        scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ユーザー発話用タグ（右寄せ、青系）。
        self.chat_text.tag_configure(
            "user",
            foreground="#66d9ef",
            justify=tk.RIGHT,
            lmargin1=60,
            lmargin2=60,
        )
        # システム応答用タグ（左寄せ、緑系）。
        self.chat_text.tag_configure(
            "system",
            foreground="#7CFC00",
            justify=tk.LEFT,
            rmargin=60,
        )
        # ラベル用タグ（role ごとに寄せ方向を分ける）。
        self.chat_text.tag_configure(
            "label_user",
            foreground="#ffffff",
            font=_pick_font(8),
            justify=tk.RIGHT,
            lmargin1=60,
            lmargin2=60,
        )
        self.chat_text.tag_configure(
            "label_system",
            foreground="#ffffff",
            font=_pick_font(8),
            justify=tk.LEFT,
            rmargin=60,
        )

    def _set_dialogue_ui_state(self, active: bool) -> None:
        # 対話アクティブ状態に合わせてボタンの有効・無効とステータス文言を切り替える。
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
        if self._ui_dialogue_active:
            return
        self._clear_chat()
        self._ui_dialogue_active = True
        self._set_dialogue_ui_state(active=True)
        self.engine_manager.start_session(self.session_id)
        logger.info("[GUI] 対話開始")

    def end_dialogue(self) -> None:
        if not self._ui_dialogue_active:
            return
        self.engine_manager.stop_session(self.session_id)
        self._ui_dialogue_active = False
        self._set_dialogue_ui_state(active=False)
        logger.info("[GUI] 対話終了")

    def close_gui(self) -> None:
        if self.is_closing:
            return
        self.is_closing = True
        logger.info("[GUI] 終了処理を開始します。")
        if self._ui_dialogue_active:
            self.engine_manager.stop_session(self.session_id)
        self.engine_manager.delete_session(self.session_id)
        self.root.destroy()

    def _refresh_engine_state(self) -> None:
        """エンジン状態を監視"""
        if self.is_closing:
            return
        # UI の状態とセッションの状態をチェック
        session = self.engine_manager.get_session(self.session_id)
        if session and not session.is_active and self._ui_dialogue_active:
            self._ui_dialogue_active = False
            self._set_dialogue_ui_state(active=False)
        self.root.after(250, self._refresh_engine_state)

    def _poll_engine_events(self) -> None:
        """エンジンからのイベントをポーリング"""
        if self.is_closing:
            return
        session = self.engine_manager.get_session(self.session_id)
        if not session:
            self.root.after(100, self._poll_engine_events)
            return

        # イベントキューから内部的には取らず、エンジンのコールバック経由で受け取る方が効率的
        # ここでは placeholder
        self.root.after(100, self._poll_engine_events)

    def _clear_chat(self) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.configure(state=tk.DISABLED)

    def _append_chat(self, role: str, text: str) -> None:
        """role='user' or 'system' のメッセージをチャットウィンドウに追記する。"""
        label = "User" if role == "user" else "System"
        label_tag = "label_user" if role == "user" else "label_system"
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"{label}\n", label_tag)
        self.chat_text.insert(tk.END, f"{text}\n", role)
        self.chat_text.configure(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def _poll_chat_queue(self) -> None:
        # エンジンイベントで chat イベントを受け取る方式に変更
        # 本バージョンでは不要だが、後方互換性用に placeholder
        if self.is_closing:
            return
        self.root.after(100, self._poll_chat_queue)

    def _poll_status_queue(self) -> None:
        # エンジンイベントで status イベントを受け取る方式に変更
        if self.is_closing:
            return
        self.root.after(100, self._poll_status_queue)


def main() -> None:
    parser = argparse.ArgumentParser(description="DialBB multimodal client launcher")
    parser.add_argument(
        "config_file",
        nargs="?",
        default=str(DEFAULT_CONFIG_FILE),
        help="runtime config yaml path",
    )
    args = parser.parse_args()

    # 設定ファイルの読み込み
    config_file = Path(args.config_file).expanduser().resolve()
    if not config_file.exists():
        raise SystemExit(MISSING_CONFIG_GUIDANCE)

    config_data: dict = {}
    with config_file.open(encoding="utf-8") as fp:
        config_data = yaml.safe_load(fp) or {}

    stt_cfg = config_data.get("stt") or {}
    dialbb_cfg = config_data.get("dialbb") or {}
    main_cfg = config_data.get("main") or {}

    stt_key_file = stt_cfg.get("key_file")
    dialbb_config = dialbb_cfg.get("config_file")
    loop_period = float(main_cfg.get("loop_period", 0.1))
    max_user_wait_time = float(main_cfg.get("max_user_wait_time", 30.0))
    mic_gain = float(stt_cfg.get("mic_gain", 1.0))

    # 設定ファイルのディレクトリからの相対パスを解決
    base_dir = config_file.parent
    if stt_key_file and not Path(stt_key_file).is_absolute():
        stt_key_file = str((base_dir / stt_key_file).resolve())
    if dialbb_config and not Path(dialbb_config).is_absolute():
        dialbb_config = str((base_dir / dialbb_config).resolve())

    if stt_key_file:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = stt_key_file
        logger.info("[SYSTEM] STTキー設定: %s", stt_key_file)
    else:
        logger.warning("[SYSTEM] STTキー未設定: mm_client_config.yml を確認してください。")

    if dialbb_config:
        logger.info("[SYSTEM] DialBB設定: %s", dialbb_config)
    else:
        logger.warning("[SYSTEM] DialBB設定未指定: mm_client_config.yml を確認してください。")

    logger.info("[SYSTEM] 起動: エンジンベースマルチモーダルクライアント")

    # エンジンマネージャを作成
    session_config = SessionConfig(
        dialbb_config=dialbb_config,
        stt_key_file=stt_key_file,
        loop_period=loop_period,
        max_user_wait_time=max_user_wait_time,
        mic_gain=mic_gain,
    )

    def on_engine_event(_session_id: str, event: DialogueEvent) -> None:
        """エンジンからのイベントハンドラ（GUI の更新用）"""
        # 対応するセッションの GUI コントローラへイベントを通知
        logger.debug("[MAIN] Engine event: %s", event.event_type)

    engine_manager = DialogueEngineManager(session_config, event_callback=on_engine_event)
    session_id = engine_manager.create_session()

    root = tk.Tk()
    _controller = MultimodalGuiController(
        root=root,
        engine_manager=engine_manager,
        session_id=session_id,
    )

    logger.info("[SYSTEM] GUIの『対話開始』で初回発話から対話を開始します。")

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("[SYSTEM] Ctrl+C を受信。終了処理を開始します。")
        _controller.close_gui()

    logger.info("[SYSTEM] 停止しました。")


if __name__ == "__main__":
    main()
