# DialBB音声マルチモーダルクライアント

## 1. 全体の仕組み
1. エントリポイントで 4 スレッドを起動  
MAINスレッド/STTスレッド/DialBBスレッド/TTSスレッド
2. スレッド間は queue.Queue で非同期連携  
［STT→MAIN→DialBB→MAIN→TTS→MAIN］
3. 終了制御は共通 stop_event で一元管理：start_mm_client.py  

## 1.1. スレッド間メッセージ仕様

- Queueを用いたメッセージ通信の詳細は [message_spec](docs/message_spec.md) を参照。

## 2. 実装ファイル
| ファイル名 | 概要 |
|---|---|
| start_multimodal_client.py | クライアント全体の起動エントリポイント。各ワーカスレッドとQueueを初期化して実行を開始する。 |
| asr/google_stt_client.py | Google Cloud Speech-to-Text を使ったストリーミング音声認識を担当する。 |
| main/main_module.py | メインモジュール。STT/DialBB/TTS間のメッセージを中継し、終了制御を行う。 |
| main/dialbb_client.py | DialBB連携ワーカー。DialogueProcessor を呼び出して対話メッセージを生成する。 |
| tts/speech_synthesizer.py | 音声合成ワーカー（現状はスタブ実装）。TTS要求を処理して完了結果を返す。 |
| main/messages.py | スレッド間でやり取りするメッセージ型（dataclass/enum）を定義する。 |

## 3. 主要アーキテクチャ
- Main ハブ型：main_module.py  
Main がイベント集約・状態管理・ルーティングを担当し、各ワーカーは単機能化。  
- メッセージ駆動設計  ：messages.py
dataclass と Enum でスレッド間でやり取りするデータを型として明示。  
- 非同期ポーリング処理  
Queue の timeout/get_nowait を使ってブロックを抑えたループ実装、タイムアウトは0.1秒で設定  

## 4. 使っている技術
- 音声認識: Google Cloud Speech-to-Text（STT） ストリーミング API  
google_stt_client.py
- 音声入力: PyAudio（Windows は pyaudiowpatch フォールバック）  
audio_input.py
- 音声合成: Google Cloud Text-to-Speech (TTS)とpygame（現状はスタブ実装）  
speech_synthesizer.py
- 対話エンジン接続: DialBB の DialogueProcessor を呼び出して応答を生成  
dialbb_client.py

## 5. 依存関係の位置づけ
- プロジェクト全体は Poetry 管理  
pyproject.toml
- mm_client で重要な依存は google-cloud-speech、pyaudio/pyaudiowpatch など  
pyproject.toml

## 6. インストール方法

1. `pip install ./dialbb-x.x.x-py3-none-any.whl`  
site-packages\にはdialbb, mm_client をインストール
1. `pip show dialbb`  
インストールしたdialbbのバージョンが表示されること

## 7. 起動方法
### 7.1 起動コマンド

1. `dialbb-mm-client`

### 7.2 設定ファイル（config.yml）
- 既定の設定ファイル: `mm_client/config/config.yml`
- 起動時に引数で設定ファイルを1つ指定可能: `dialbb-mm-client <config_file>`

| 設定項目 | 概要 |
|---|---|
| `stt.key_file` | Google STT サービスアカウントキー(JSON)へのパス
| `dialbb.config_file` | DialBB のアプリ設定(`config.yml`)へのパス

パスは絶対パス、または設定ファイルからの相対パスで指定できる。
