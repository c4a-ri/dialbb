# DialBB Multimodal Server 仕様書

## 1. 目的

本書は `dialbb.multimodal.server` が提供するサーバ機能の外部仕様を定義する。
対象は以下の 2 つである。

- REST API によるセッション管理
- WebSocket API による対話制御と音声ストリーミング

本仕様は実装コード `dialbb/multimodal/server.py`、`dialbb/multimodal/engine.py`、`dialbb/multimodal/core.py` に基づく。

## 2. サーバ概要

### 2.1 役割

サーバは FastAPI 上で動作し、クライアントごとの対話セッションを管理する。
各セッションは内部的に以下のワーカースレッド群を持つ。

- STT worker
- DialBB worker
- TTS worker
- Core dialogue engine worker
- audio log worker（`audio_logging=true` の場合のみ）

### 2.2 通信方式

- セッション作成、開始、停止、削除、一覧取得は REST API を利用する
- 対話中の制御と音声授受は WebSocket を利用する

### 2.3 セッションの単位

- セッションは UUID 形式の `session_id` で識別される
- WebSocket は `session_id` 単位で接続される
- 同一 `session_id` に対して複数の WebSocket 接続を保持できる
- 音声イベントは同一 `session_id` に接続している全クライアントへ配信される

## 3. 起動仕様

### 3.1 エントリポイント

CLI エントリポイントは `dialbb-mm-server` である。

### 3.2 起動コマンド

```sh
dialbb-mm-server <config_file> [--host HOST] [--port PORT] [--debug] [--audio_logging]
```

### 3.3 引数

| 引数 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `config_file` | 必須 | なし | DialBB アプリ設定ファイルへのパス |
| `--host` | 任意 | `0.0.0.0` | 待受ホスト |
| `--port` | 任意 | `5000` | 待受ポート |
| `--debug` | 任意 | `False` | Uvicorn の reload を有効化 |
| `--audio_logging` | 任意 | `False` | 音声ログ機能を有効化 |

### 3.4 環境変数

- 起動時にカレントディレクトリの `.env` を読み込む
- `.env` の読込は `python-dotenv` により行われる

## 4. 設定仕様

サーバは `config_file` から YAML を読み込む。
現行実装で参照されるトップレベル設定は以下のみである。

| 設定キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `cycle` | float | `0.1` | コアエンジンのループ周期 |
| `user_timeout` | float | `30.0` | ユーザ発話待ちタイムアウト秒数 |
| `audio_logging` | bool | `False` | 音声ログ保存の有効化 |

補足:

- CLI の `--audio_logging` が指定されても、現行実装では YAML の `audio_logging` 値で上書きされる
- `sample_rate` は現行実装では `16000` 固定である
- `language_code` は現行実装では `ja-JP` 固定である

## 5. REST API 仕様

### 5.1 共通

- Content-Type は JSON を前提とする
- 認証は実装されていない
- CORS は全許可である

### 5.2 `GET /health`

サーバ生存確認を行う。

レスポンス例:

```json
{
  "status": "ok",
  "service": "mm-client-server"
}
```

### 5.3 `POST /sessions`

新規セッションを生成する。

レスポンス:

- ステータスコード: `201`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 5.4 `POST /sessions/{session_id}/start`

指定セッションを開始する。

正常時:

```json
{
  "status": "started"
}
```

異常時:

- `400 Failed to start session`

失敗条件:

- `session_id` が存在しない
- セッションがすでに開始済みである
- 内部開始処理に失敗した

### 5.5 `POST /sessions/{session_id}/stop`

指定セッションを停止する。

正常時:

```json
{
  "status": "stopped"
}
```

異常時:

- `400 Failed to stop session`

失敗条件:

- `session_id` が存在しない
- セッションが未開始またはすでに停止済みである

### 5.6 `DELETE /sessions/{session_id}`

指定セッションを削除する。

正常時:

```json
{
  "status": "deleted"
}
```

異常時:

- `404 Session not found`

補足:

- アクティブなセッション削除時は内部的に停止処理を行ってから削除する

### 5.7 `GET /sessions`

アクティブなセッション一覧を返す。

レスポンス例:

```json
{
  "sessions": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

補足:

- 未開始のセッションは一覧に含まれない
- 停止済みセッションも一覧に含まれない

## 6. WebSocket API 仕様

### 6.1 接続先

```text
/dialogue/ws/{session_id}
```

### 6.2 接続条件

- 対象 `session_id` が存在すること

存在しない場合:

- WebSocket close code: `1008`
- reason: `Session not found`

### 6.3 接続完了イベント

接続成功直後にサーバは以下を送信する。

```json
{
  "event": "joined_session",
  "payload": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 6.4 クライアントからの送信形式

クライアントは JSON で `action` を含むオブジェクトを送信する。

```json
{
  "action": "..."
}
```

## 7. WebSocket 受信アクション仕様

### 7.1 `start_dialogue`

セッション開始を要求する。

送信例:

```json
{
  "action": "start_dialogue"
}
```

動作:

- 内部的に `engine_manager.start_session(session_id, settings)` を実行する

エラー時:

```json
{
  "event": "error",
  "payload": {
    "message": "Failed to start dialogue"
  }
}
```

補足:

- 同一セッションを REST と WebSocket の両方から開始しようとすると二重開始となり失敗する

### 7.2 `end_dialogue`

セッション停止を要求する。

送信例:

```json
{
  "action": "end_dialogue"
}
```

動作:

- 先に `stop_audio` イベントを送信する
- その後でセッション停止処理を行う

停止失敗時:

```json
{
  "event": "error",
  "payload": {
    "message": "Failed to stop dialogue"
  }
}
```

### 7.3 `cancel_tts`

再生中 TTS のキャンセルを要求する。

送信例:

```json
{
  "action": "cancel_tts"
}
```

動作:

- セッションの `tts_cancel_requested` を `True` にする
- TTS worker へ cancel を通知する
- サーバは `stop_audio` を push 通知する

存在しないセッションに対して呼び出された場合は内部的に `HTTPException(404)` が発生し、WebSocket ハンドラでは個別補足されない。

### 7.4 `send_audio_chunk`

音声チャンクを送信する。

送信例:

```json
{
  "action": "send_audio_chunk",
  "audio_data": "<base64>"
}
```

動作:

- `audio_data` を base64 デコードする
- デコード成功時はセッションの `audio_chunk_queue` に投入する
- `audio_logging` 有効時はユーザ音声ログ用バッファにも蓄積する

異常系:

- base64 デコード失敗時はサーバログに warning を出す
- クライアントには明示エラーを返さない
- `audio_data` が空文字列の場合も明示エラーを返さない

期待フォーマット:

- PCM16 系の音声チャンクを想定
- STT worker へそのまま転送されるため、クライアントは STT 実装と整合する形式で送る必要がある

### 7.5 `tts_segment_playback_done`

クライアントで 1 セグメントの TTS 再生が完了したことを通知する。

送信例:

```json
{
  "action": "tts_segment_playback_done",
  "utterance_id": 3,
  "segment_index": 1,
  "segment_count": 4
}
```

必須条件:

- `utterance_id > 0`
- `segment_index > 0`
- `segment_count > 0`

条件を満たさない場合:

```json
{
  "event": "error",
  "payload": {
    "message": "invalid tts playback ack"
  }
}
```

補足:

- 古い `utterance_id` に対する通知は stale として無視される
- 本通知を受けるまでサーバは原則として次の TTS セグメント送出待機を継続する
- 再生完了通知が一定時間内に来ない場合、内部待機はタイムアウトし、そのセグメント送信処理は失敗扱いになる

### 7.6 `stop_audio_done`

クライアントが `stop_audio` 制御を受理したことを通知する。

送信例:

```json
{
  "action": "stop_audio_done",
  "reason": "cancel"
}
```

動作:

- サーバはログ出力のみ行う
- 応答イベントは返さない

### 7.7 未対応アクション

未対応の `action` を送信した場合:

```json
{
  "event": "error",
  "payload": {
    "message": "Unsupported action"
  }
}
```

## 8. サーバからの送信イベント仕様

### 8.1 `joined_session`

接続成功通知。

```json
{
  "event": "joined_session",
  "payload": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 8.2 `audio_data`

TTS 音声セグメントを通知する。

```json
{
  "event": "audio_data",
  "payload": {
    "audio": "<base64>",
    "format": "wav",
    "utterance_id": 3,
    "segment_index": 1,
    "segment_count": 4
  }
}
```

項目仕様:

| 項目 | 型 | 説明 |
|---|---|---|
| `audio` | string | WAV 音声データの base64 文字列 |
| `format` | string | 現行実装では常に `wav` |
| `utterance_id` | integer | 発話単位の連番 |
| `segment_index` | integer | 1 始まりのセグメント番号 |
| `segment_count` | integer | 当該発話の総セグメント数 |

補足:

- 音声は `16kHz`, `LINEAR16`, `1ch` の WAV セグメントとして生成される
- テキストは文単位と文字数上限に基づき分割され、その単位で合成と配信が行われる
- クライアントはセグメントごとに `tts_segment_playback_done` を返す必要がある

### 8.3 `stop_audio`

クライアントに現在の音声再生停止を要求する。

```json
{
  "event": "stop_audio",
  "payload": {
    "reason": "cancel",
    "utterance_id": 3
  }
}
```

`reason` の値:

- `cancel`: バージインまたは明示的 TTS キャンセル
- `end_dialogue`: 対話終了要求に伴う停止

### 8.4 `error`

WebSocket レベルの入力不正または制御失敗時に通知する。

```json
{
  "event": "error",
  "payload": {
    "message": "Unsupported action"
  }
}
```

## 9. 対話状態遷移

### 9.1 基本遷移

1. `POST /sessions` でセッション作成
2. `/dialogue/ws/{session_id}` に接続
3. `start_dialogue` または `POST /sessions/{session_id}/start` で開始
4. サーバが初回 DialBB 要求を内部生成
5. システム応答を TTS 化し `audio_data` を送信
6. クライアントは音声再生後に `tts_segment_playback_done` を返す
7. ユーザ音声を `send_audio_chunk` で送信
8. STT の最終認識後に DialBB 応答生成へ進む
9. `end_dialogue` または `POST /sessions/{session_id}/stop` で停止

### 9.2 バージイン

システム発話中にユーザ発話が検出され、最終応答でない場合はバージインが発生する。

動作:

- サーバ内部で TTS キャンセル要求を立てる
- クライアントへ `stop_audio` を送る
- 以後のシステム音声送出を抑止する
- ユーザ最終発話が確定すると、その発話内容で DialBB 処理を継続する

### 9.3 最終応答

DialBB 応答が `is_final=True` の場合:

- サーバは最終応答として TTS を再生する
- 再生中は新規 STT 入力を無効化する
- 最終再生完了後にセッションは内部的に対話終了状態へ遷移する

## 10. 音声ログ仕様

`audio_logging=true` の場合、サーバは作業ディレクトリ配下に音声ログを保存する。

保存先:

```text
audio_logs/{session_id}/
```

生成物:

- `manifest.jsonl`
- ユーザ音声 WAV ファイル
- システム音声 WAV ファイル

`manifest.jsonl` の各レコード項目:

- `sequence`
- `timestamp_ns`
- `source`
- `audio_format`
- `file_name`
- `transcript`
- `utterance_id`
- `segment_index`
- `segment_count`

補足:

- ユーザ音声ログは最終認識テキスト確定時にフラッシュされる
- テキストが空白のみの場合、そのユーザ音声は保存されない

## 11. 制約事項

- 認証、認可はない
- セッション情報はプロセスメモリ上にのみ保持され、永続化されない
- `GET /sessions` はアクティブセッションのみ返す
- WebSocket の `cancel_tts` 失敗時は HTTP 例外がそのまま上位へ伝播しうる
- `send_audio_chunk` の入力形式検証は最小限で、base64 として復号できるかのみを主に見ている
- `audio_logging` の有効可否は実装上 YAML 設定値が優先される

## 12. 実装参照

- `dialbb/multimodal/server.py`
- `dialbb/multimodal/engine.py`
- `dialbb/multimodal/core.py`
- `dialbb/multimodal/tts/speech_synthesizer.py`