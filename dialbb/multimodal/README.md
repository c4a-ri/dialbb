# DialBB音声マルチモーダルサーバ

## 概要

`dialbb.multimodal` は、DialBB を音声対話用のサーバとして動かすための実装です。現行版は FastAPI ベースで、REST API によるセッション管理と WebSocket による音声対話を提供します。

内部では 1 セッションごとに以下のワーカが動作します。

- STT worker
- DialBB worker
- TTS worker
- Core dialogue engine worker
- audio log worker（`audio_logging` 有効時のみ）

Google Cloud Speech-to-Text と Google Cloud Text-to-Speech を利用するため、実行環境では Google Cloud の認証情報が必要です。

## 主要モジュール

| ファイル | 役割 |
| --- | --- |
| `server.py` | FastAPI アプリ本体。REST API、WebSocket 接続、クライアント向けイベント送信を担当します。 |
| `engine.py` | セッション単位の状態を管理し、ワーカースレッドを起動・停止します。 |
| `core.py` | 対話の状態遷移を扱うコアロジックです。UI には依存しません。 |
| `main/dialbb_client.py` | DialBB アプリ設定ファイルを使って対話エンジンを呼び出します。 |
| `asr/google_stt_client.py` | WebSocket で受け取った PCM16 音声を Google STT に流し、認識イベントへ変換します。 |
| `tts/speech_synthesizer.py` | システム発話を Google TTS で合成し、セグメント単位でクライアントへ返します。 |
| `docs/message_spec.md` | ワーカ間のメッセージ仕様です。 |
| `docs/server_spec.md` | REST API / WebSocket API の詳細仕様です。 |

## 現行の処理フロー

1. クライアントは `POST /sessions` でセッションを作成します。
2. クライアントは `/dialogue/ws/{session_id}` に WebSocket 接続します。
3. `start_dialogue` または `POST /sessions/{session_id}/start` により、セッションごとのワーカ群が起動します。
4. 音声入力は `send_audio_chunk` で base64 化した PCM16 音声として送信され、STT worker が Google STT に流します。
5. STT の中間結果はバージイン検知に使われ、確定結果は DialBB worker に送られます。
6. DialBB 応答を受けた Core engine は `system_message` を通知し、続けて TTS worker に合成を依頼します。
7. TTS worker は発話テキストを短いセグメントに分割し、各セグメントを個別に合成して `audio_data` として送信します。
8. クライアントは各音声セグメントの再生完了後に `tts_segment_playback_done` を返します。サーバはこの通知を待ってから次のセグメントを送ります。
9. DialBB が最終応答を返した場合は、その再生完了後に `final` イベントを出して対話を終了状態へ遷移させます。

### バージイン

- システム発話中に STT の中間認識または確定認識が入ると、Core engine は TTS 停止を要求します。
- サーバは `stop_audio` イベントをクライアントへ送り、再生停止を促します。
- 割り込み時の最終認識結果には `aux_data` として `barge_in: true` が DialBB に渡されます。

### 無音タイムアウト

- システム発話終了後はユーザ発話待ち状態に入ります。
- `user_timeout` 秒を超えて発話が来ない場合、Core engine は DialBB に `user_silence` を送ります。

### 音声ログ

- `audio_logging` が有効な場合、ユーザ音声とシステム音声を `audio_logs/<session_id>/` に保存します。
- ユーザ音声は確定認識時に 1 発話分をまとめて WAV 保存します。
- システム音声は送信セグメントごとに保存し、`manifest.jsonl` にメタデータを追記します。

## 起動方法

CLI エントリポイントは `dialbb-mm-server` です。

```sh
dialbb-mm-server <config_file> [--host HOST] [--port PORT] [--debug] [--audio_logging]
```

- `config_file` には DialBB のアプリ設定ファイルを指定します。
- `--audio_logging` を指定すると、設定ファイル側の値に加えて音声ログを強制的に有効化できます。

## 設定ファイル

現行実装では、サーバ設定は DialBB アプリ設定ファイル内の `multimodal` セクションから読み込みます。後方互換のため、同じキーをトップレベルに置いた場合も読み取れます。

```yaml
multimodal:
  audio_logging: true
  cycle: 0.1
  user_timeout: 10.0
```

読み込まれるキーは以下です。

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `audio_logging` | `false` | 音声ログ保存の有無 |
| `cycle` | `0.1` | Core engine のメインループ周期（秒） |
| `user_timeout` | `30.0` | ユーザ発話待ちタイムアウト（秒） |

## REST API

- `GET /health`
- `POST /sessions`
- `POST /sessions/{session_id}/start`
- `POST /sessions/{session_id}/stop`
- `DELETE /sessions/{session_id}`
- `GET /sessions`

`GET /sessions` は現在アクティブなセッションのみ返します。

## WebSocket API

接続先:

```text
/dialogue/ws/{session_id}
```

### クライアント -> サーバ

- `start_dialogue`
- `end_dialogue`
- `cancel_tts`
- `send_audio_chunk`
- `tts_segment_playback_done`
- `stop_audio_done`

`send_audio_chunk` は以下の形式です。

```json
{
  "action": "send_audio_chunk",
  "audio_data": "<base64 encoded PCM16>",
  "aux_data": {"key": "value"}
}
```

### サーバ -> クライアント

- `joined_session`
- `system_message`
- `audio_data`
- `stop_audio`
- `error`

`system_message` は音声送信前のテキスト通知です。`audio_data` には `audio`、`format`、`utterance_id`、`segment_index`、`segment_count`、必要に応じて `aux_data` が含まれます。

## 動作確認用クライアント

- `examples/client_example.html`

このサンプルはセッション作成、WebSocket 接続、マイク入力、`tts_segment_playback_done` 応答まで含めた現行フローに対応しています。

## 参考資料

- 詳細な外部仕様: [docs/server_spec.md](docs/server_spec.md)
- ワーカ間メッセージ仕様: [docs/message_spec.md](docs/message_spec.md)
