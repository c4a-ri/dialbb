# DialBB音声マルチモーダルクライアント

## 1. 全体の仕組み
1. エントリポイント(GUI)で 4 スレッドを起動  
MAINスレッド/STTスレッド/DialBBスレッド/TTSスレッド
2. スレッド間は queue.Queue で非同期連携  
	- 主な通信イメージ： STT → MAIN → DialBB → MAIN → TTS → MAIN
	- 通信Queueには、情報受け渡しの`データQueue` と 動作指示の`制御Queue` がある
3. GUI（Tkinter）の対話開始/対話終了で、対話状態と音声入力受付を制御  
4. アプリ終了は GUI の終了ボタンで共通 stop_event を発行し、全スレッドを停止  

## 1.1. 使っている技術
- 音声認識: Google Cloud Speech-to-Text（STT） ストリーミング API  
- 音声合成: Google Cloud Text-to-Speech (TTS) と pygame  
- 対話エンジン接続: DialBB の DialogueProcessor を呼び出して応答を生成  

　※Google Cloud STT/TTSを使用するためにサービスアカウントキーが必要です。  

## 1.2. スレッド間メッセージ仕様

- Queueを用いたメッセージ通信の詳細は [メッセージ仕様](docs/message_spec.md) を参照。

## 2. 実装ファイル
| ファイル名 | 概要 |
|---|---|
| start_mm_client.py | クライアント全体の起動エントリポイント。GUIと各ワーカスレッド、Queue、Eventを初期化して実行を開始する。 |
| main/main_module.py | メインモジュール。STT/DialBB/TTS間のメッセージを中継し、対話状態を制御する。 |
| asr/google_stt_client.py | 音声認識ワーカ。Google Cloud STT を使ったストリーミング音声認識を担当する。 |
| asr/audio_input.py | PyAudio を使って マイク音声を非同期で取得し、PCM16のバイト列として逐次取り出す。 |
| main/dialbb_client.py | DialBB連携ワーカー。対話開始要求時に初回応答を生成し、以降の対話を処理する。 |
| tts/speech_synthesizer.py | 音声合成ワーカー。Google Cloud TTS で合成した音声を pygame で再生する、再生キャンセルに対応。 |
| main/messages.py | スレッド間でやり取りするメッセージ型（dataclass/enum）を定義する。 |

## 3. 主要アーキテクチャ
- Main ハブ型：main_module.py  
Main がイベント集約・状態管理・ルーティングを担当し、各ワーカーは単機能化。  
イベント監視ループは`ループ周期-処理時間`を計算し一定間隔でループするようにsleepする、stop_eventを受信した時にループは終了。ループ周期はdefault=0.1秒で設定（configで変更可）  
- メッセージ駆動設計  ：messages.py
dataclass と Enum でスレッド間でやり取りするデータを型として明示。  
- Event駆動の対話制御  
`conversation_active_event` と `stt_enabled_event` で対話状態と音声入力受付を切り替える。  
- 非同期ポーリング処理  
Queue の get_nowait を使ってブロックを抑えたループ実装。  

## 5. インストール方法

1. `pip install ./dialbb-x.x.x-py3-none-any.whl`  
dialbb, mm_client の2つがインストールされる
1. `pip show dialbb`  
インストールしたdialbbのバージョンが表示されること

### 5.1 macOS 固有の前提条件

macOS で動作させる場合は、以下を事前に準備してください。

1. PortAudio（pyaudio のバックエンド）  
PortAudio は pyaudio のバックエンドです。未導入の場合、起動時にエラーで落ちます。  
以下のコマンドでインストールしてください。
	```sh
	brew install portaudio
	```
2. Tk 対応 Python
macOS 標準の Python は Tkinter が付属していない場合があります。
Homebrew や python.org からインストールした Python を使ってください。
	```sh
	brew install python-tk  # Homebrew Python を使っている場合
	```
3. マイク権限
macOS はマイクへのアクセス権限を **システム設定 → プライバシーとセキュリティ → マイク** で許可する必要があります。
権限なしで起動すると STT ワーカーがエラー終了し、GUI に「異常終了」と表示されます。

## 6. 起動方法
### 6.1 起動コマンド

1. `dialbb-mm-client 　※default以外のconfigファイルを使用する場合は引数にパスを指定する`

### 6.2 GUI操作

- `対話開始`: GUI から Main へ start コマンドを送り、Main が初回 DialBB 要求を発行する。
- `対話終了`: 対話を停止し、各スレッドは待機状態へ戻る（音声入力は受け付けない）。
- `終了`: `stop_event` を発行して全ワーカースレッドを終了し、GUIを閉じる。

### 6.2.1 最終応答（対話終了フロー）

DialBB が `"final": true` を返した場合、自動的に対話が終了します：

1. **最終応答の受信**: Main が `is_final=true` 付きの DialbbResponse を受け取る
2. **再生中の入力禁止**: TTS が最終応答を再生する間、ユーザーからの新しい音声入力と割り込み（バージイン）を禁止する
3. **対話終了に遷移**: 最後の音声合成再生が完了すると、自動的に対話終了状態に遷移し、`conversation_active_event` がクリアされる
4. **状態リセット**: 内部の全ての対話関連フラグ（`user_speaking`, `system_speaking`, `is_final_response`など）がリセットされる
5. **GUI 待機**: GUI の 「対話開始」ボタンで再び対話を開始できる

### 6.3 設定ファイル（config.yml）
- 既定の設定ファイル: `mm_client/config/config.yml`
- 起動時に引数で設定ファイルを1つ指定可能: `dialbb-mm-client <config_file>`

| 設定項目 | 概要 |
|---|---|
| `stt.key_file` | Google STT サービスアカウントキー(JSON)へのパス
| `stt.mic_gain` | マイクゲイン（`1.0`=原音、`<1.0`=減衰、`>1.0`=増幅）
| `dialbb.config_file` | DialBB のアプリ設定(`config.yml`)へのパス
| `main.loop_period` | Main ループ周期（秒）
| `main.max_user_wait_time` | ユーザ発話待ちタイムアウト（秒、超過で `user_silence` を送信）

パスは絶対パス、または設定ファイルからの相対パスで指定できる。
