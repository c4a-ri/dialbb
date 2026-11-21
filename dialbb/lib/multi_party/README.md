# 多人数会話（multi_party）の仕様

人間と複数の DialBB アプリケーションが、共通のハブを介して会話するためのモジュールです。
参加者を spoke（スポーク）と呼び、各スポークが Socket.IO クライアントとしてハブに接続します。
参加・退出は会話の途中でも可能で、ハブ用の参加者設定ファイルは不要です。

## 構成

| ファイル | 役割 |
| --- | --- |
| `hub.py` | 参加者を管理し、発話・参加・退出を参加済みのスポークへ配信するサーバー |
| `dialbb_spoke.py` | DialBB セッションとハブを接続するスポーク |
| `user_spoke.py` | 人間がターミナルから参加する CLI スポーク |
| `user_spoke_gui.py` | 人間が日本語 IME を使って入力できる GUI スポーク |
| `events.py` | DialBB に渡す参加・退出・沈黙の特殊発話の定義 |

ハブは発話の中継を担当します。発話するかどうかの判断は各 DialBB アプリケーションが行います。
各スポークは独立した対話履歴とセッションを持ちます。

## 起動方法

以下はリポジトリのルートで実行します。各プロセスには同じ Python 環境を使用してください。

```sh
python -m pip install -e ".[multi-party]"
```

ハブ、DialBB、人間のスポークを、それぞれ別のターミナルで起動します。
DialBB 側には使用するモデルの API キーなども設定してください。

```sh
# ハブ
python -m dialbb.lib.multi_party.hub

# DialBB（設定ファイル、参加者名の順に指定）
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config1.yml 田中

# 人間（CLI または GUI のいずれか）
python -m dialbb.lib.multi_party.user_spoke 山田
python -m dialbb.lib.multi_party.user_spoke_gui 山田
```

| コマンド | 引数・オプション | 既定値 |
| --- | --- | --- |
| `hub` | `--host` | `localhost` |
| `hub` | `--port` | `5000` |
| `dialbb_spoke` | `config_file`、`my_name` | いずれも必須 |
| `user_spoke` / `user_spoke_gui` | `my_name` | 必須 |
| すべてのスポーク | `--hub-url` | `http://localhost:5000` |

CLI は接続後に Enter を押すと参加し、以後は入力した発話を Enter で送信します。
空白だけの入力は送信しません。GUI は Join ボタンで参加し、Send ボタンまたは
Ctrl+Enter で送信します。GUI の Enter は送信には使わず、IME の変換確定に使えます。
GUI は入力の前後の空白を取り除いて送信します。

CLI と DialBB は Ctrl+C、GUI はウインドウを閉じると終了します。
接続だけでは参加者として登録されず、`join` の成功後に配信対象になります。

## ハブの通信仕様

ハブは単一の会話を扱い、参加者を Socket.IO の接続 ID（`sid`）と名前で管理します。
参加者名は空白だけではない文字列で、同時に参加している名前と重複できません。
名前の前後の空白はハブでは除去しません。

### スポークから送るイベント

| イベント | データ | 成功時の ACK |
| --- | --- | --- |
| `join` | `{"speaker": "山田"}` | `{"ok": true}` |
| `utterance` | `{"speaker": "山田", "utterance": "こんにちは"}` | `{"ok": true}` |

`join` は同じ接続・同じ名前で再送しても成功し、参加通知は再配信しません。
同じ接続で別の名前に変更することはできません。
`utterance` は参加済みの接続から、その接続に登録した名前を指定して送ります。
発話は空白だけではない文字列に限り、ハブでは本文を加工せず配信します。

失敗時は `{"error": "エラー文字列"}` を返します。

| 条件 | エラー文字列 |
| --- | --- |
| 名前が文字列でない、空文字、空白のみ | `participant name must be a nonempty string` |
| 同じ接続が別名で参加しようとした | `already joined with another name` |
| 他の接続が同名で参加済み | `participant already joined` |
| 未参加、または発話者名が登録名と異なる | `join the conversation first` |
| 発話が文字列でない、空文字、空白のみ | `empty utterance` |

### ハブから配信するイベント

| イベント | データ | 配信先 |
| --- | --- | --- |
| `participant_joined` | `speaker`、`participants` | 新規参加者自身を含む参加者全員 |
| `broadcast_utterance` | `speaker`、`utterance`、`participants` | 発話者自身を含む参加者全員 |
| `participant_left` | `speaker`、`participants` | 残っている参加者全員 |

`speaker` は発話・参加・退出した人の登録名です。
`participants` はイベント発生時点の参加者名のリストで、参加通知では参加者を含み、
退出通知では退出者を含みません。接続を切断すると退出扱いになります。
専用の退出イベントをスポークから送る必要はありません。

過去の発話の保存・再配信は行いません。途中参加したスポークが受信するのは、
自分の参加通知以降のイベントです。

## DialBB スポークの動作

### セッション開始

`DialBBSpoke.connect(hub_url)` は次の順に処理します。

1. ハブへ接続する。
2. `DialogueProcessor.process(..., initial=True)` を呼び、セッションを作成する。
   初期リクエストは `user_id: my_name`、`aux_data: {"participants": []}` とする。
3. ハブに `join` を送り、登録する。
4. 有効な場合は沈黙タイマーを開始し、初期応答の `system_utterance` を送信する。
5. 受信イベントの処理用ワーカーを開始する。

初期化中・登録中の受信イベントはキューで待機します。
参加に失敗した場合は切断し、エラーにします。

### 受信イベントから DialBB リクエストへの変換

初期化後は、同じ `session_id` に対して次のリクエストを送ります。
`aux_data.participants` には各受信イベントに付属する参加者一覧を渡します。

| イベント | `user_id` | `user_utterance` |
| --- | --- | --- |
| 他者の発話 | `speaker` | 発話本文 |
| 参加 | 参加者名 | `"(joined the conversaion)"` |
| 退出 | 退出者名 | `"(left the conversaion)"` |
| 沈黙タイマー | `""` | `"(silence)"` |

`conversaion` という綴りは現行プロトコルの一部です。
特殊発話は [events.py](events.py) の `JOINED`、`LEFT`、`SILENCE` を使用します。
自分自身の参加通知も DialBB に渡しますが、自分の発話の配信は DialBB に渡しません。

応答の `system_utterance` が空でなければ、スポーク名を `speaker` としてハブに送ります。
空なら送信せず待機します。`final` による自動切断の処理はありません。

受信コールバックはイベントをキューに積み、単一のワーカーが順に DialBB を呼び出します。
同じスポーク内で複数の対話処理は並行実行しません。
ワーカーで例外または `SystemExit` が発生した場合は、エラーを記録して切断します。
CLI 起動時はこのエラーにより終了コード `1` で終了します。

## LLMDialogue の多人数会話設定

発話判断には [LLMDialogue](../../builtin_blocks/llm_dialogue/llm_dialogue.py) の
`multi_party` 設定を使用できます。`system_name` はスポークの `my_name` と一致させてください。
CLI は `DialogueProcessor` のコンストラクターに `{"my_name": my_name}` を渡しますが、
`system_name` を自動的に書き換える処理はありません。

```yaml
language: ja
silence_timeout: 10  # 秒。blocks と同じ階層に置く
blocks:
  - name: llm_dialogue
    block_class: dialbb.builtin_blocks.llm_dialogue.LLMDialogue
    input:
      dialogue_history: dialogue_history
      aux_data: aux_data
    output:
      system_utterance: system_utterance
      aux_data: aux_data
      final: final
    system_name: 田中
    first_system_utterance: 好きな食べ物について話しましょう
    prompt_template: prompt.txt
    model: openai:gpt-4.1-mini
    multi_party:
      silence: 黙る
      turn_taking_strategy: after_all_other_speak
      required_participants:
        - 田中
        - 山田
```

| `multi_party` 内の設定 | 既定値 | 意味 |
| --- | --- | --- |
| `silence` | 未指定 | この文字列と一致する応答を空の発話に変換する |
| `turn_taking_strategy` | 未指定 | `after_all_other_speak` または `wait_n_turns` |
| `turns_to_wait` | `1` | `wait_n_turns` で待つ発話数。正の整数 |
| `required_participants` | `[]` | 初期発話までに参加を待つ user ID のリスト |

`multi_party` は辞書（空の辞書も可）または真偽値を受け付け、未指定・`false` で無効です。
互換性のため `true` も使え、その場合は上記の設定をブロック直下から読みます。

### 初期発話と発話順

`required_participants` の全員がそろうまで空の応答で待機します。
そろったリクエストで、そのセッションの `first_system_utterance` を一度だけ返します。
未指定なら初期化時に返します。開始後に必須参加者が退出・再参加しても初期発話は繰り返しません。

開始後の発話順は、最後の空でないシステム発話以降の履歴で判定します。

- `after_all_other_speak`: 現在参加している自分以外の全員が、少なくとも一度発話したら応答します。
  他の参加者がいない場合は応答しません。
- `wait_n_turns`: 他者の発話が `turns_to_wait` 回以上あれば応答します。同じ人の複数の発話も数えます。
- 未指定: 空でない入力に応答します。参加・退出の特殊発話も対象になります。

参加・退出・沈黙の通知は、どちらの戦略でも通常の発話回数に含めません。
参加・退出を受け取った時点でも、すでに待機条件を満たしていれば応答することがあります。
`aux_data.no_response_required` が真の場合は、開始後の応答を抑制します。
空の応答や `silence` による待機は、最後の発話以降のカウントをリセットしません。

参加者一覧は入力の `aux_data.participants` を優先し、なければ履歴中の最新値を使います。
明示的な空リストは「参加者なし」と扱います。
LLM に渡す履歴では他者の話者名に `user_id`、自分の話者名に `system_name` を使い、
参加・退出の特殊発話も含めます。プロンプト内の `{participants}` は入力の参加者一覧に置換できます。
`silence: 黙る` の場合、前後の空白と `「」` を除いた応答が `黙る` と一致すれば発話しません。

## 沈黙タイマー

設定ファイルのトップレベルの `silence_timeout` を `dialbb_spoke` の CLI が読み込みます。
単位は秒で、有限の非負数を指定します。未指定または `0` で無効です。
プログラムから使う場合は `DialBBSpoke(..., silence_timeout=10)` のように指定します。

参加登録後、誰の発話も受信しない状態が指定時間続くと、自分の DialBB に沈黙イベントを送ります。
このイベント自体はハブには送信しません。参加者一覧にはタイマー発火時の最新値を使います。

- 自分の発話の配信も含め、空白だけではない発話を受信すると、その場でタイマーをリセットします。
- 参加・退出ではタイマーをリセットしません。
- キューのイベントを優先し、DialBB の処理中に沈黙リクエストを重ねません。
- 沈黙イベントの処理後は、次の沈黙イベントまで指定時間待ちます。

`LLMDialogue` は開始後の沈黙イベントで通常の発話順の条件を外し、
会話を再開する指示をプロンプトに追加して LLM を呼び出します。
初期発話前の `required_participants` の待機と `no_response_required` による応答抑制は優先されます。
LLM が `silence` に一致する応答を返した場合は、この場合も送信しません。

## 運用上の制約と関連資料

各スポークの Socket.IO クライアントは自動再接続を無効にしています。
再参加する場合はスポークを起動し直してください。退出済みの名前は再利用できます。
ハブには認証、会話ルームの分離、履歴の永続化の実装はありません。
また、スポーク間の発話権や沈黙タイマーを一括管理しないため、複数の DialBB が同時に発話することがあります。
タイマー値を参加者ごとに変えると、同時に沈黙を検出することを避けやすくなります。

- [日本語サンプルと起動手順](../../../sample_apps/multi_party_ja/README.md)
- [ハブ・スポーク・LLMDialogue のテスト](../../../tests/test_multi_party.py)
- [GUI 入力のテスト](../../../tests/test_multi_party_gui.py)
