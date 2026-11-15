# DialBB 分散トレーサ

このブランチは、対話システム構築フレームワーク DialBB のfeature/multimodal ブランチに OpenTelemetry による分散トレーシングを組み込んだものです。音声認識（STT）、対話処理、LLM 呼び出し、音声合成（TTS）、WebSocket 送信にかかる時間と、ワーカ間のキュー待ちを Jaeger で確認し、応答遅延の原因を調査できます。

**設定・起動方法・各 span の定義・計測上の注意点は、[マルチモーダルサーバの README](dialbb/multimodal/README.md#opentelemetry--jaeger-による遅延調査) を参照してください。**

## トレースの構成

目的に応じて、次の2つのサービスに分けて記録します。

| Jaeger の Service | 主な Operation | 計測範囲 |
| --- | --- | --- |
| `dialbb-dialogue` | `dialogue.turn` | ユーザ音声の WebSocket 受信から、最後の応答音声セグメントの送信完了まで |
| `dialbb-process` | `dialbb.process` | `DialogueProcessor.process()` の開始から応答まで。各ブロックと内部の LLM 呼び出しなどを含む |

音声対話側では、STT → Core → DialBB worker → Core → TTS → WebSocket の処理を、ワーカ間でトレースコンテキストを引き継いで追跡します。DialBB 内部処理は独立した trace ID で記録し、音声ターンの `turn.id`、span link、相互参照用の trace ID 属性で関連付けます。

`dialogue.turn` の終点はサーバでの音声送信完了です。ブラウザで実際に音が鳴り始めるまでの時間とは異なります。途中の音声セグメントの再生完了待ちはターンに含まれ、最後のセグメントの再生完了待ちは別トレースに記録されます。

## 主な計測対象

- **音声認識**：入力音声の受信から確定認識まで、発話終了通知から確定認識までの待ち時間。
- **ワーカ間通信**：メッセージ作成から処理開始までのキュー待ち、送信元・受信先スレッド。
- **DialBB 内部処理**：各ブロックの実行、DST のスロット抽出・結果解析、STN の遷移条件評価・アクション実行、LLMDialogue の発話生成。
- **LLM 呼び出し**：LangChain 経由の `llm.invoke` の実行時間。
- **音声合成・送信**：セグメントごとの TTS API 呼び出し、WebSocket 送信、クライアントの再生完了通知待ち。
- **応答までの経過時間**：STT の発話終了通知または確定認識から、最初の応答音声の送信完了まで。

音声データ・認識文・プロンプトは span の属性に追加しません。

## 有効化と起動

リポジトリのルートで依存関係を反映します。

```sh
uv sync
```

既存の Jaeger または OpenTelemetry Collector の OTLP/HTTP 受信先を、`.env` または環境変数に設定します。以下はローカルの受信先を使う例です。

```dotenv
OTEL_TRACES_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

この URL は Jaeger UI ではなく、トレースの送信先です。STT・TTS 用の Google Cloud 認証情報と、使用する LLM の認証情報も設定してから起動します。

```sh
uv run dialbb-mm-server sample_apps/llm_dialogue_ja/config_mm.yml --port 5000
```

DST＋STN の計測には、次のサンプルを使えます。

```sh
uv run dialbb-mm-server sample_apps/dst_stn_ja/config.yml --port 5000
```

トレースは OTLP/HTTP（Protobuf）でバックグラウンド送信します。`OTEL_TRACES_ENABLED=true` または OTLP endpoint の指定がある場合に exporter を起動し、`OTEL_SDK_DISABLED=true` でサーバによる初期化を抑止できます。

内部処理を詳細に計測するブロックは、アプリ設定の `blocks[].name` を指定して選択できます。省略時は全ブロックが対象です。

```yaml
telemetry:
  trace_blocks: [dst, manager]
```

## 計測結果のレポート

Jaeger UI からエクスポートした JSON を、処理別の回数・合計・平均・最大時間を含む Markdown レポートに変換できます。

```sh
uv run python -m dialbb.util.trace_report trace1.json trace2.json -o trace-report.md
```

音声ターンと DialBB 内部処理は別トレースのため、両方を集計する場合はそれぞれの JSON を指定してください。`--details` を付けると、トレースごとの内訳と自己時間も表示します。

## トレース機能の追加・変更ファイル

`dialbb/` 配下に新規追加した実装ファイルは、次の2つです。

- [dialbb/util/telemetry.py](dialbb/util/telemetry.py)：OpenTelemetry の初期化、span の生成、ワーカ間のコンテキスト引き継ぎ、ターンの計測。
- [dialbb/util/trace_report.py](dialbb/util/trace_report.py)：トレース JSON から Markdown レポートを生成。

これらを実際の処理に組み込むため、既存の `dialbb/main.py`、`dialbb/builtin_blocks/` 内の LLM・DST・STN 関連ファイル、`dialbb/multimodal/` 内のサーバ・Core・STT・TTS・DialBB ワーカ関連ファイルにも計測コードを追加しています。依存関係とレポート生成コマンドは `pyproject.toml`・`uv.lock`、使い方と計測設定は README・サンプル設定に反映しています。

検証用に `tests/test_telemetry.py` と `tests/test_trace_report.py` も追加しています。

## 関連資料

- [マルチモーダルサーバの詳細・トレーシング仕様](dialbb/multimodal/README.md)

## ライセンス

DialBB は [Apache License 2.0](LICENSE) の下で公開されています。

(c) C4A Research Institute, Inc.
