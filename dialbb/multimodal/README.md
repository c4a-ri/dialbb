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
- `examples/client_example.html` は直前のシステム発話について、どの程度再生済みだったかを `system_utterance_completion_ratio` として `send_audio_chunk.aux_data` に自動付与します。

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
  stop_at_barge_in: true
  system_barge_in_ratio: 0.0
  tts_speaking_rate: 1.0
  tts_voice_name: ja-JP-Neural2-B
  user_timeout: 10.0
```

読み込まれるキーは以下です。

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `audio_logging` | `false` | 音声ログ保存の有無 |
| `cycle` | `0.1` | Core engine のメインループ周期（秒） |
| `stop_at_barge_in` | `true` | ユーザのバージイン検知時に再生中のシステム発話を停止するか |
| `system_barge_in_ratio` | `0.0` | システム発話中の `partial_transcript` を DialBB に先行送信して割り込ませる確率 |
| `tts_speaking_rate` | `1.0` | Google TTS の発話速度 |
| `tts_voice_name` | `null` | Google TTS の話者名。未指定時は `language_code` に応じた既定音声 |
| `user_timeout` | `10.0` | ユーザ発話待ちタイムアウト（秒） |

トップレベルの `language` も参照し、`ja` なら `ja-JP`、`en` なら `en-US` を STT/TTS の `language_code` として使います。その他の値は現在 `ja-JP` 扱いです。

`stop_at_barge_in` が `false` の場合、システム発話中にユーザ発話を検知しても TTS 停止は要求しません。`system_barge_in_ratio` により `partial_transcript` を DialBB に先行送信する場合も同様です。ただし、確定したユーザ発話は通常どおり DialBB に送られ、`aux_data.barge_in` も付与されます。

`system_barge_in_ratio` は `0.0` 以上で有効です。`1.0` なら毎回、`0.5` なら半分の確率で、システム発話中の `partial_transcript` を DialBB に先行送信します。`0.0` は既定値で、先行送信は行いません。partial 由来の応答は、ユーザがまだ話している途中でも保留せずに TTS を開始します。

## ノーコードツールとの統合

* DialBB-NC（ノーコードツール）で作成・編集した DialBB アプリケーション設定を、マルチモーダルサーバの `config_file` として指定できます。

  1. DialBB-NC で対話アプリケーションを作成または編集し、設定ファイルを書き出します。
  2. 設定画面の **Multimodal** で、音声ログ、バージイン、タイムアウト、TTS 話速・話者などの設定を必要に応じて編集します。

* ノーコードツールGUIのボタンからマルチモーダルを実行できます
  1. 編集した設定ファイルを指定して、マルチモーダルサーバを起動します。

* ノーコードツールのインストール、起動、アプリケーション作成・書き出しの詳細は、[DialBBノーコードツールのドキュメント](../../docs/no-code/index-ja.md)を参照してください。

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
  "aux_data": {
    "system_utterance_completion_ratio": 0.6
  }
}
```

`aux_data.system_utterance_completion_ratio` は任意です。値域は `0.0` から `1.0` で、直前のシステム発話がどこまで再生されたかを表します。クライアント実装によっては他の `aux_data` と併用できます。

### サーバ -> クライアント

- `joined_session`
- `system_message`
- `audio_data`
- `stop_audio`
- `error`

`system_message` は音声送信前のテキスト通知です。`audio_data` には `audio`、`format`、`utterance_id`、`segment_index`、`segment_count`、必要に応じて `aux_data` が含まれます。

## クライアントの使い分け

| クライアント | 用途 | 主な利用環境 |
| --- | --- | --- |
| `examples/client_example.html` | [開発者用]ブラウザから API、WebSocket、マイク入力を手動確認するための Web クライアント | 開発 PC のブラウザ |
| `examples/client_example.py` | [開発者用]音声入出力を含む Python 側の接続・処理をデバッグするためのクライアント | PyAudio を利用できる開発 PC |
| `mm_frontend` | [ユーザ用]スマホ・タブレットで実際に使う PWA クライアント | Android、iPhone、iPad、タブレット |

いずれも、先にマルチモーダルサーバを起動しておきます。

```sh
dialbb-mm-server <config_file> --host 0.0.0.0 --port 5000
```

開発 PC 以外の端末から接続する場合は、`<config_file>` を実行した PC の LAN 内 IP アドレスを使用します。例えば `192.168.1.10` の場合、サーバ URL は `http://192.168.1.10:5000` です。

### Web クライアント: `examples/client_example.html`

ブラウザ上で接続手順やイベントを確認したい場合に使用します。HTML ファイルをブラウザで開き、次の順で操作します。

1. Server URL に `ws://localhost:5000`、または接続先サーバの `ws://<host>:5000` を入力します。
2. **作成** を押してセッション ID を作成します。
3. **接続**、**対話開始** の順に押します。
4. **マイク開始** を押し、ブラウザのマイク利用を許可して発話します。
5. 終了時は **対話終了**、**切断** の順に押します。

WAV ファイルは事前にサーバの `dialbb/multimodal/examples/data/` に配置してください。
サーバを起動し、`http://localhost:5000/examples/client_example.html` を開くと、
そのディレクトリの `*.wav` 一覧がドロップダウンに自動で表示されます。
ファイル選択ボタンや登録操作はありません。対話開始後、**選択して送信** のリストで
WAV を選ぶだけで送信します。同じ WAV も再選択できます。
ファイルを追加したらページを再読み込みしてください。
一覧取得に失敗した場合はテキスト欄に赤字でエラーを表示します。サーバの起動とURLを確認し、ページを再読み込みしてください。
ページ表示時に一覧を取得できなかった場合も、サーバへの接続時に自動で再取得します。

HTML をローカルから直接開く場合も、指定した Server URL の WAV 一覧を自動取得します。
WAV が未配置の場合は空の一覧と配置先の案内を表示します。

送信時に WAV を16kHz・モノラルの PCM16 に変換し、末尾に既定 **1.5秒** の無音を追加します。
**末尾の無音（秒）** で0.5〜5秒に調整できます。元の WAV ファイルは変更しません。
STT に実時間で入力するため、100ms 単位で分割送信します。
マイク入力との混在を防ぐため WAV 送信開始時にマイクを停止し、送信中は別の音声入力を無効にします。
**対話終了** または **切断** で、ファイルの残りの送信も中断します。

このクライアントは、受信イベントとエラーを画面で確認する API デバッグ向けです。ユーザ音声送信時には、直前のシステム発話の再生進捗を `system_utterance_completion_ratio` として自動送信します。

### Python クライアント: `examples/client_example.py`

端末のマイク・スピーカーを使用した Python クライアントの動作確認に使用します。`pyaudio` と `websockets` が利用可能な Python 環境で実行してください。

```sh
python dialbb/multimodal/examples/client_example.py
```

引数を省略すると `ws://localhost:5000` に接続し、セッションを自動作成します。接続先を指定する場合は次のように実行します。

```sh
python dialbb/multimodal/examples/client_example.py ws://192.168.1.10:5000
```

既存のセッション ID を使う場合は、セッション ID とサーバ URL をこの順に指定します。

```sh
python dialbb/multimodal/examples/client_example.py <session_id> ws://192.168.1.10:5000
```

起動すると対話を開始してマイク音声を送信し、受信した TTS 音声を再生します。停止は `Ctrl+C` です。

### モバイル PWA: `mm_frontend`

スマホ・タブレットの利用には `mm_frontend` を使用します。ビルド結果はサーバが `/` で配信します。

```sh
cd mm_frontend
npm install
npm run build
```

ビルド後、サーバを起動し、端末のブラウザで `https://<host>:5000/` を開きます。開発時は `npm run dev` で起動した URL を利用できますが、実機でマイクを使う本番運用にはマルチモーダルサーバから配信する PWA を使用してください。

別サーバへ接続する検証時は、URL に `?server=https://<host>:5000` を付与して接続先を上書きできます。

## スマホ・タブレットへの PWA インストールと利用

PWA のインストールとマイク利用にはセキュアコンテキストが必要です。実機では `https://` で公開してください。`http://localhost` は開発端末自身でのみ例外的に利用できますが、別のスマホ・タブレットから `http://<LAN IP>` へ接続する構成では HTTPS が必要です。また、ファイアウォールで HTTPS のポートを許可してください。

### Android（Chrome / Edge）

1. `https://<host>:5000/` を開きます。
2. ブラウザのメニューから **アプリをインストール** または **ホーム画面に追加** を選びます。
3. 表示される確認画面で **インストール** を選びます。
4. ホーム画面の `DialBB Mobile PWA` アイコンから起動します。

### iPhone / iPad（Safari）

1. Safari で `https://<host>:5000/` を開きます。
2. 共有ボタンを押し、**ホーム画面に追加** を選びます。
3. 名前を確認して **追加** を押します。
4. ホーム画面のアイコンから起動します。

### PC版（Chrome / Edge）  ※参考

1. ブラウザ で `http://localhost:5000/` を開きます。
2. アドレスバーの横の"アプリのインストール"アイコンからインストールを行います。
3. 追加したアイコンまたはスタートメニューから起動します。

### PWA の使い方

1. PWA を起動し、初回だけマイク利用を許可します。
2. **開始** を押すとセッションを作成して対話を開始します。
3. 端末に向かって発話します。認識したユーザ発話とシステム発話が画面に表示され、応答音声が再生されます。
4. システム発話中に話すと、バージインとして再生を停止して次の発話を受け付けます。
5. **終了** を押すと、音声入力・再生・WebSocket 接続を終了します。

音声が出ない、またはマイクが利用できない場合は、ブラウザまたは OS のサイト権限でマイクを許可し、端末とサーバが HTTPS で接続されていることを確認してください。

## 参考資料

- 詳細な外部仕様: [docs/server_spec.md](docs/server_spec.md)
- ワーカ間メッセージ仕様: [docs/message_spec.md](docs/message_spec.md)

## OpenTelemetry / Jaeger による遅延調査

OpenTelemetry の OTLP/HTTP（Protobuf） で既存の Jaeger または Collector に送信できます。
処理区間を span として記録し、ワーカ間のメッセージに
内部用のトレースコンテキストを持たせています。音声・認識文・プロンプトは span の属性に追加しません。

依存関係を `uv sync` で反映した後、`.env` または起動環境に次を設定してください。
`OTEL_EXPORTER_OTLP_ENDPOINT` は Jaeger UI ではなく OTLP/HTTP（Protobuf） の受信先です。

```dotenv
OTEL_TRACES_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

次のいずれかで起動し、音声対話を行います。

```bash
uv run dialbb-mm-server sample_apps/llm_dialogue_ja/config_mm.yml --port 5000
uv run dialbb-mm-server sample_apps/dst_stn_ja/config.yml --port 5000
```

Jaeger では次の2サービスで分類して検索します。

| Service | Operation | 計測区間 |
| --- | --- | --- |
| `dialbb-dialogue` | `dialogue.turn` | ユーザ音声の WebSocket 受信から最後の応答音声の送信完了まで |
| `dialbb-process` | `dialbb.process` | ワーカから呼ぶ `DialogueProcessor.process()` の開始から応答まで。設定された全ブロックと内部 API を含む |

2つの TracerProvider にそれぞれ固定の Resource `service.name` を設定します。
`.env` の `SERVICE_NAME` / `OTEL_SERVICE_NAME` は、この2つの分類を変更しません。
1回の呼び出しは別々の trace ID で記録し、共通の `turn.id` と span link で関連付けます。
サーバ側の `dialogue.call_process` からも、ライブラリの呼び出し時間を確認できます。
その属性 `dialbb.process.trace_id` を Jaeger の Trace ID 検索に使うと内部処理へ移動できます。
内部処理の `dialogue.trace_id` / `dialogue.span_id` は呼び出し元を示します。
既存の Collector を使う場合はその HTTP endpoint に置き換えてください。
送信先は `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` で traces 専用に上書きできます。
通常の `OTEL_EXPORTER_OTLP_ENDPOINT` では `/v1/traces` が自動付与されます。
traces 専用の設定を使う場合は `http://localhost:4318/v1/traces` のようにパスまで指定してください。
認証ヘッダーや TLS は OpenTelemetry の標準 OTLP 環境変数を使用します。

`OTEL_TRACES_ENABLED=true` または OTLP endpoint の指定がある場合だけ exporter を起動します。
`OTEL_SDK_DISABLED=true` を指定するとサーバによる初期化を抑止します。
2つの provider はサーバ専用に管理し、アプリ側のグローバル TracerProvider は変更・終了しません。
サーバが生成した provider は終了時に残りの span を送信して shutdown します。
送信は BatchSpanProcessor でバックグラウンド実行します
（[OpenTelemetry の exporter 設定](https://opentelemetry.io/docs/languages/python/exporters/)）。

| span | 測定対象・調査の観点 | ソースファイル |
| --- | --- | --- |
| `dialogue.turn` | 発話に対応する音声チャンクの WebSocket 受信から、最後の応答音声セグメントの送信完了まで。1ターン全体を表す親 span。 | [telemetry.py](../util/telemetry.py) |
| `stt.utterance` | 入力音声の受信から確定認識まで。発話時間・キュー待ち・STT への転送・認識待ちを含みます。 | [telemetry.py](../util/telemetry.py) |
| `stt.transcription_wait` | 発話終了通知から確定認識までの待ち時間。 | [telemetry.py](../util/telemetry.py) |
| `core.process_stt_event.queue_wait` | STT イベント生成から Core が処理するまで。Core の周期の影響を含みます。 | [core.py](core.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（待ち時間のspan生成） |
| `dialbb.request.queue_wait` | Core の要求作成から DialBB worker が取り出すまで。初期化待ちや先行要求の処理待ちも含みます。 | [main/dialbb_client.py](main/dialbb_client.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（待ち時間のspan生成） |
| `dialogue.call_process` | サーバのワーカから `process()` を呼んで戻るまで。内部の内訳は `dialbb-process` を参照します。 | [main/dialbb_client.py](main/dialbb_client.py) |
| `dialbb.process` / `dialbb.block` | 対話処理全体と各設定ブロックの実行時間。`block.name` / `block.class` で重いブロックを識別できます。常に `dialbb-process` の別トレースになります。 | [main.py](../main.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（span生成） |
| `core.process_dialbb_response.queue_wait` | DialBB の応答作成から Core の受信まで。 | [core.py](core.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（待ち時間のspan生成） |
| `tts.request.queue_wait` | Core の TTS 要求作成から TTS worker の処理開始まで。前の発話の再生待ちも影響します。 | [tts/speech_synthesizer.py](tts/speech_synthesizer.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（待ち時間のspan生成） |
| `llm.invoke` | LLMDialogue・DST・シナリオ関数内の LLM 呼び出し。リトライがある場合は呼び出しごとに分かれます。 | [llm_dialogue.py](../builtin_blocks/llm_dialogue/llm_dialogue.py)、[dst_with_llm.py](../builtin_blocks/dst_with_llm/dst_with_llm.py)、[builtin_scenario_functions.py](../builtin_blocks/stn_management/builtin_scenario_functions.py) |
| `tts.synthesize` | 各セグメントの Google TTS 呼び出し時間。 | [tts/speech_synthesizer.py](tts/speech_synthesizer.py) |
| `tts.send_and_playback` / `tts.playback_wait` | 音声送信処理とブラウザの再生完了 ACK を待つ時間。再生待ちは合成の遅さと区別してください。 | [server.py](server.py) |
| `browser.schedule_wait` / `browser.send` | イベントループへの投入待ちと実際の WebSocket 送信。 | [server.py](server.py) |
| `dialogue.speech_end_to_audio_sent` | STT の発話終了通知を受けてから最初の応答音声を WebSocket 送信し終わるまで。 | [server.py](server.py) |
| `dialogue.final_transcript_to_audio_sent` | 確定認識から最初の応答音声の送信完了まで。 | [server.py](server.py) |
| `dialbb.initialize` / `stt.initialize` / `tts.initialize` | 各 worker の初期化時間。ターン処理とは別のトレースです。 | [main/dialbb_client.py](main/dialbb_client.py)、[asr/google_stt_client.py](asr/google_stt_client.py)、[tts/speech_synthesizer.py](tts/speech_synthesizer.py)（左記span順） |

発話に由来する STT → Core → DialBB 要求 → Core → TTS → WebSocket は同じ trace ID でつながります。
DialBB 要求内の `dialbb.process` とその子 span は、常に `dialbb-process` の別 trace ID になります。
親 span `dialogue.turn` の属性 `session.id` はブラウザのセッション ID、`turn.id` はターン固有の ID です。
`turn.outcome=audio_sent` は最後の音声の送信完了、`tts_cancelled` は割り込み等による中断を示します。
送信失敗・対話処理のエラー・セッション終了時にも、未完了のターンを終了します。
初回応答は `dialogue.initial_turn` から始まり、入力音声がないため `dialogue.turn` の対象外です。
音声チャンクごとの span は生成しません。

ターンの開始時刻は、Google STT の `speech_event_time` を、STT に送った PCM16 音声の位置と照合し、
該当チャンクを WebSocket で受信した時刻まで遡って設定します。チャンク単位の時刻精度です。
これにより、連続送信される発話前の無音を通常は除外します。
発話開始通知がない場合は、前の認識結果より後の最初の受信チャンクを使用するため、無音時間が含まれる場合があります。
対応する受信情報もない場合は認識イベント時刻にフォールバックします。
どの開始位置を使ったかは `turn.start_boundary` で確認できます。

最後の音声セグメントの再生完了 ACK は、返送完了より後の処理なので、
別トレースの `tts.playback_wait` として記録し、元のターンへの span link と `turn.id` を付けます。
途中のセグメントの再生待ちは次の音声送信を遅らせるため、同じターンの内訳に含みます。
応答音声はサーバでの WebSocket 送信完了を終点とし、ブラウザの受信完了や再生開始は保証しません。
queue_wait はメッセージ作成時点を起点とし、計測メタデータは WebSocket ペイロードに含めません。
通常の処理 span の `thread.name` / `thread.id` と、キュー経由の
`queue.producer.thread` / `queue.consumer.thread` から、スレッド間の受け渡しを確認できます。

`dialogue.speech_end_to_audio_sent` は Google STT が発話終了通知を確定認識より前に返した場合に記録します。
終了通知がない場合にも `dialogue.final_transcript_to_audio_sent` は確認できます。
この2つは処理の実行区間ではなく、STT の通知から最初の応答音声の送信完了までの経過時間です。
Jaeger では `dialogue.turn` の直下に表示し、`tts.send_and_playback` の子にはしません。
送信完了時に保存済みの STT 通知時刻を開始時刻に指定するため、`dialogue.call_process` より前から始まります。
実際の処理順序は `stt.utterance` → `dialogue.call_process` → `tts.synthesize` → `browser.send` で確認してください。
いずれもブラウザで実際に音が鳴り始めるまでの時間や、サーバに終了通知が届く前の VAD 判定・通信時間は含みません。
`tts.request` には途中のセグメントの再生待ちも含まれます。全体の長さだけで合成が遅いと判断せず、子 span を確認してください。

### DialBB 内部処理の機能別計測

`telemetry.trace_blocks` の省略時は全ブロックの詳細計測を有効にします。
`sample_apps/dst_stn_ja/config.yml` では次のように `dst` と `manager` を明示しています。
名前は `blocks[].name` に対応し、未定義の名前は起動時にエラーになります。

```yaml
telemetry:
  trace_blocks: [dst, manager]
```

Jaeger ではサービス **`dialbb-process`**、**Span / Span Name（旧 Operation）`dialbb.process`** を選択してください。
`process()` 1回ごとに独立したトレースを生成するため、検索結果の処理時間は音声入力・TTS・キュー待ちを含みません。
元の `dialogue.call_process` に span link を付け、音声ターンがある場合は `turn.id` も記録します。
音声ターンの終了や切断が起きても、このトレースは `process()` の終了まで計測します。
初回応答も記録され、`request.initial=true` で区別できます。

`sample_apps/llm_dialogue_ja/config_mm.yml` を使う場合は、ブロック名に合わせて
`trace_blocks: [llm_dialogue]` と指定します。分離の仕組みは DST＋STN と共通です。
この設定はワーカーの span の送信を停止する設定ではありません。
ワーカーの span は別トレースとして送信され、`dialbb.process` の内部処理だけを別 trace ID で確認できます。

ワーカーが同じトレースに見える場合は、サーバを再起動して新しく対話し、
その `dialbb.process` span の属性を確認してください。

| 属性 | 確認する値 |
| --- | --- |
| `dialbb.config_file` | 実際に読み込んだ config の絶対パス |
| `dialbb.trace_blocks` | `dst, manager` または `llm_dialogue` などの対象ブロック |
| `dialbb.trace_mode` | 常に `independent`（独立トレース） |
| `trace.scope` | 独立トレースでは `dialbb.process` |

起動ログの `Tracing configuration:` にも config のパス・対象ブロック・分離モードと
実行中の `main.py` のパスを出します。属性がない記録は、この診断属性の追加前に生成された可能性があります。
span link で関連付けたワーカーと、同じ trace ID の親子 span は区別してください。

| Operation | 測定対象 | ソースファイル |
| --- | --- | --- |
| `dialbb.process` | `DialogueProcessor.process()` の開始から応答を返すまで。履歴処理、全ブロックの実行、応答データの作成を含む | [main.py](../main.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（span生成） |
| `dialbb.block` | ブロックの `process()` 全体 | [main.py](../main.py)（呼び出し）、[telemetry.py](../util/telemetry.py)（span生成） |
| `llm_dialogue.generate_utterance` | LLMDialogue のプロンプト構築・LLM 呼び出し・応答整形 | [llm_dialogue.py](../builtin_blocks/llm_dialogue/llm_dialogue.py) |
| `dst.format_history` | DST に渡す対話履歴の文字列化 | [dst_with_llm.py](../builtin_blocks/dst_with_llm/dst_with_llm.py) |
| `dst.extract_slots` | スロット抽出全体。LLM・リトライ・解析・値の正規化を含む | [dst_with_llm.py](../builtin_blocks/dst_with_llm/dst_with_llm.py) |
| `dst.parse_result` | LLM の JSON 応答解析 | [dst_with_llm.py](../builtin_blocks/dst_with_llm/dst_with_llm.py) |
| `stn.transition` | 遷移先探索と遷移時アクション | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `stn.check_condition` | 遷移条件1件の評価 | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `stn.perform_actions` | 遷移時のアクション列の実行 | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `stn.generate_utterance` | システム発話内の変数・関数の展開 | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `stn.generate_confirmation` | 確認要求の生成 | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `stn.scenario_function.<関数名>` | 設定されたシナリオ関数・組み込み関数の個別呼び出し | [stn_manager.py](../builtin_blocks/stn_management/stn_manager.py) |
| `llm.invoke` | DST・シナリオ関数内の LLM 呼び出し1回 | [llm_dialogue.py](../builtin_blocks/llm_dialogue/llm_dialogue.py)、[dst_with_llm.py](../builtin_blocks/dst_with_llm/dst_with_llm.py)、[builtin_scenario_functions.py](../builtin_blocks/stn_management/builtin_scenario_functions.py) |

実行された機能だけ span が生成されます。機能別 span と LLM span には `block.name`、`block.class`、
`session.id`、`trace.scope=dialbb.process` を付けるため、Operation とブロック名で絞って集計できます。
親の所要時間は子の所要時間を含むので、親子の値を加算しないでください。
`dialogue.turn` は音声ターン全体、`dialbb.process` は対話処理だけとして別々に集計します。
Jaeger の検索はトレースを表示します。平均やパーセンタイルの継続的な集計には、Collector 等で span からメトリクスを生成する設定が別途必要です。

`trace_blocks: []` は機能別 span を抑制しますが、`dialbb.process` と全ブロックの
`dialbb.block` は引き続き `dialbb-process` の独立トレースとして記録します。
exporter の有効化は前述の OTEL 環境変数で行います。

### Jaeger JSON から処理時間の報告書を作る

Jaeger UI から JSON をエクスポートし、次のコマンドで Markdown の報告書を生成できます。
対象は Jaeger UI の `{"data": [{"traceID": "...", "spans": [...]}]}` 形式です。
時間の単位と親子関係は [Jaeger UI のデータモデル](https://github.com/jaegertracing/jaeger/blob/main/internal/uimodel/model.go) に従います。
OTLP JSON は対象外です。サーバや Collector への追加設定は必要ありません。

```sh
# 対話処理全体と、各処理にかかった時間をまとめる
uv run python -m dialbb.util.trace_report trace.json --root dialbb.process -o report.md

# 複数ファイルをまとめて集計する（対象の処理を絞らず、すべて集計）
uv run python -m dialbb.util.trace_report trace1.json trace2.json -o report.md

# TTS 要求だけに絞る
uv run python -m dialbb.util.trace_report trace.json --root tts.request
```

インストール後は `dialbb-trace-report` コマンドでも実行できます。
`--root` は Operation 名の完全一致です。指定した処理とその子孫だけを対象とし、
span link でつながる別トレースは合算しません。音声ターンの JSON に詳細計測の
`dialbb.process` が入っていない場合は、Jaeger でその Operation のトレースも別途エクスポートしてください。

出力例（説明用の仮の数値）:

```text
- tts.request [6.414s] …TTS 要求全体（途中セグメントの再生待ちを含む）（1回）
    - tts.send_and_playback [5.7s] …音声送信と再生完了待ち（ターン終了まで）（2回）
    - tts.synthesize [714ms] …音声合成 API 呼び出し（2回）
```

各行の `[時間]` は、その処理にかかった時間の合計です。複数ファイルの同じ処理もまとめます。
例では TTS 全体が 6.414 秒、そのうち音声送信・再生待ちが 5.7 秒、音声合成が 714 ミリ秒です。
全体の時間には、下に並ぶ処理の時間が含まれます。
ブロック名が違う処理は別々に表示し、同じ記録を重複して読み込んだ場合は1回だけ数えます。

最後に、処理別の「回数・合計・平均・最大」を表で表示します。合計時間が長い順に並びます。
平均・最大は、読み込んだ記録の処理1回あたりの値です。

トレースごとの内訳や「自己時間」も必要な場合は `--details` を付けてください。

```sh
uv run python -m dialbb.util.trace_report trace1.json trace2.json --root dialbb.process --details -o detailed-report.md
```

詳細表示には「自己時間」も出します。これは、その処理の時間から子の処理にかかった時間を除いたものです。
同時に動いた子の時間は重複して差し引きません。自己時間には待機や未計測の処理も含まれます。
同時実行や再帰呼び出しがあると、子の時間の合計が全体の時間を超える場合があります。
平均・最大は、読み込んだ記録の処理1回あたりの値です。

外部 API を使わずに計測を検証するテスト:

```sh
uv run python -m unittest discover -s tests -v
```
