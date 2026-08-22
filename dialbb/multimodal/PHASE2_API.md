# DialBB Multimodal API Spec (Current)

この文書は、`dialbb.multimodal.server` の現行 API 仕様をまとめたものです。

対象コード:

- `dialbb/multimodal/server.py`
- `dialbb/multimodal/engine.py`
- `dialbb/multimodal/core.py`

## 1. サーバ起動

CLI エントリポイント:

```sh
dialbb-mm-server <config_file> [--host HOST] [--port PORT] [--debug] [--audio_logging]
```

- `config_file`: DialBB アプリの設定ファイル。
- `--host`: デフォルト `0.0.0.0`
- `--port`: デフォルト `5000`
- `--debug`: Uvicorn reload を有効化
- `--audio_logging`: 音声ログを強制有効化

起動時にカレントディレクトリの `.env` を読み込みます。

## 2. 設定仕様

`config_file` から YAML を読み込み、`multimodal` セクションを優先して参照します。
後方互換として、トップレベルにも同名キーを置けます。

```yaml
multimodal:
  audio_logging: true
  cycle: 0.1
  stop_at_barge_in: true
  system_barge_in_ratio: 0.0
  tts_speaking_rate: 1.0
  tts_voice_name: ja-JP-Neural2-B
  user_timeout: 10.0
```

| キー | 型 | デフォルト | 説明 |
| --- | --- | --- | --- |
| `audio_logging` | bool | `false` | ユーザ音声/システム音声ログを保存 |
| `cycle` | float | `0.1` | Core エンジンのループ周期（秒） |
| `stop_at_barge_in` | bool | `true` | ユーザのバージイン検知時にシステム発話を停止する |
| `system_barge_in_ratio` | float | `0.0` | `partial_transcript` を DialBB に先行送信して割り込ませる確率 |
| `tts_speaking_rate` | float | `1.0` | Google TTS の発話速度 |
| `tts_voice_name` | string \| null | `null` | Google TTS の話者名。未指定時は `language_code` に応じた既定音声 |
| `user_timeout` | float | `10.0` | ユーザ無音タイムアウト（秒） |

トップレベルの `language` も参照し、`ja` なら `ja-JP`、`en` なら `en-US` を STT/TTS の `language_code` として使います。その他の値は現在 `ja-JP` 扱いです。

## 3. REST API

### 3.1 `GET /health`

レスポンス:

```json
{
  "status": "ok",
  "service": "mm-client-server"
}
```

### 3.2 `POST /sessions`

新規セッションを作成します。

レスポンス (201):

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3.3 `POST /sessions/{session_id}/start`

指定セッションを開始します。

レスポンス:

```json
{
  "status": "started"
}
```

失敗時は `400` を返します。

### 3.4 `POST /sessions/{session_id}/stop`

指定セッションを停止します。

レスポンス:

```json
{
  "status": "stopped"
}
```

失敗時は `400` を返します。

### 3.5 `DELETE /sessions/{session_id}`

指定セッションを削除します。

レスポンス:

```json
{
  "status": "deleted"
}
```

セッションが存在しない場合は `404` を返します。

### 3.6 `GET /sessions`

現在アクティブなセッション ID 一覧を返します。

```json
{
  "sessions": ["session_id_1", "session_id_2"]
}
```

## 4. WebSocket API

接続先:

```text
/dialogue/ws/{session_id}
```

セッションが存在しない場合は接続を拒否します。

### 4.1 クライアント -> サーバ

メッセージ形式:

```json
{
  "action": "...",
  "...": "payload"
}
```

サポートされる `action`:

- `start_dialogue`
- `end_dialogue`
- `cancel_tts`
- `send_audio_chunk`
- `tts_segment_playback_done`
- `stop_audio_done`

#### `send_audio_chunk`

```json
{
  "action": "send_audio_chunk",
  "audio_data": "<base64 encoded PCM16>",
  "aux_data": {
    "system_utterance_completion_ratio": 0.6
  }
}
```

- `audio_data`: base64 の音声データ
- `aux_data`: 任意。直後の STT 結果に紐づける追加情報
- `aux_data.system_utterance_completion_ratio`: 任意。`0.0` から `1.0` の数値で、直前のシステム発話の再生完了率を表す

補足:

- この値はクライアント側で算出して送る
- バージイン時は、再生済みセグメントと再生中セグメントの進捗から算出した比率を送ってよい
- サーバはこの値を解釈せず、そのまま STT 結果に対応する `aux_data` として DialBB 側へ渡す

#### `tts_segment_playback_done`

```json
{
  "action": "tts_segment_playback_done",
  "utterance_id": 1,
  "segment_index": 1,
  "segment_count": 3
}
```

`utterance_id` / `segment_index` / `segment_count` は正の整数が必要です。不正値は `error` イベントで通知されます。

### 4.2 サーバ -> クライアント

送信形式:

```json
{
  "event": "...",
  "payload": {}
}
```

主な `event`:

- `joined_session`
- `system_message`
- `audio_data`
- `stop_audio`
- `error`

#### `system_message`

```json
{
  "event": "system_message",
  "payload": {
    "text": "...",
    "aux_data": {},
    "utterance_id": 12
  }
}
```

#### `audio_data`

```json
{
  "event": "audio_data",
  "payload": {
    "audio": "<base64>",
    "format": "wav",
    "utterance_id": 12,
    "segment_index": 1,
    "segment_count": 3,
    "aux_data": {}
  }
}
```

補足:

- `format` は現行実装では `wav`
- `aux_data` は必要時のみ 1 セグメント目へ引き継がれます

#### `stop_audio`

```json
{
  "event": "stop_audio",
  "payload": {
    "reason": "cancel",
    "utterance_id": 12
  }
}
```

## 5. 対話制御の要点

### 5.1 バージイン

- システム発話中に STT 側でユーザ発話が検知されると、サーバは TTS 停止を要求します。
- クライアントには `stop_audio` を通知します。
- `stop_at_barge_in=false` の場合、ユーザ発話を検知しても TTS 停止要求と `stop_audio` 通知は行いません。`system_barge_in_ratio` による partial 先行送信時も同様です。
- いずれの場合も、システム発話中に確定したユーザ発話には `aux_data.barge_in=true` が付与されます。
- `system_barge_in_ratio>0.0` により `partial_transcript` を DialBB へ送った場合、その応答は `user_speaking=true` でも保留せずに TTS 開始します。

### 5.2 セグメント再生同期

- サーバは `audio_data` をセグメント単位で送信します。
- 各セグメントごとに `tts_segment_playback_done` を受け取るまで次を送らない実装です。

### 5.3 最終応答

- DialBB が `final=true` を返した場合、最終音声の再生完了後に内部状態を終了へ遷移します。

### 5.4 無音タイムアウト

- `user_timeout` 秒を超えてユーザ発話が来ない場合、`user_silence` を DialBB へ送信します。

## 6. 音声ログ

`audio_logging` が有効な場合:

- 保存先: `audio_logs/<session_id>/`
- ユーザ音声: 発話単位で WAV 保存
- システム音声: セグメント単位で保存
- メタ情報: `manifest.jsonl`

## 7. 既知の注意点

- `GET /sessions` は「存在する全セッション」ではなく「アクティブなセッション」を返します。
- `service` フィールド値は `mm-client-server` です（CLI 名 `dialbb-mm-server` と文字列は異なります）。

## 8. 参考資料

- 詳細仕様: `dialbb/multimodal/docs/server_spec.md`
- ワーカ間メッセージ: `dialbb/multimodal/docs/message_spec.md`
- 動作確認用クライアント: `dialbb/multimodal/examples/client_example.html`
