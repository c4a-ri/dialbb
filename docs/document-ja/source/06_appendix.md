# Appendix

## フロントエンド

DialBBには，Web APIにアクセスするための，2種類のサンプルフロントエンドが付属しています．

### シンプルなフロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>
```

システム発話とユーザ発話を吹き出しで表示します．

`aux_data`の送信はできません．また，レスポンスに含まれるシステム発話以外の情報は表示されません．

### デバッグ用フロントエンド

以下でアクセスできます．

```
http://<ホスト>:<ポート番号>/test
```

システム発話とユーザ発話をリスト型式で表示します．

`aux_data`の送信ができます．また，レスポンスに含まれる`aux_data`も表示されます．



## DialBBのソースコードを変更する方法

GitHubリポジトリからcloneします．cloneしたディレクトリを<DialBBのディレクトリ>とします．

```sh
git clone git@github.com:c4a-ri/dialbb.git <DialBBのディレクトリ>
```

`uv`で依存関係をインストールします．このとき，DialBB本体も編集可能な形で環境に入るため，ソースコードを変更するとそのまま反映されます．

```sh
cd <DialBBのディレクトリ>
uv sync
```

起動時は`uv run`を付けて実行します．

```sh
uv run dialbb-server [--port <port>] <config file>
```

pythonファイルを指定して起動することもできます（PyCharmやVSCodeなどのIDEを用いる場合はこちらが必要です）．


```sh
uv run python <DialBBのディレクトリ>/run_server.py [--port <port>] <config file>
```


(multi_party_dialogue)=

## 多人数会話

人間や複数の DialBB アプリケーションが同じ会話に参加できます。各参加者は spoke（スポーク）と呼ばれるクライアントを使って hub（ハブ）に Socket.IO で接続します。ハブは発話と参加・退出の通知を中継します。人間はターミナルまたは GUI から参加し、各 DialBB スポークは独立したセッションを持ち、発話するタイミングを判断します。

### サンプルの起動

リポジトリのルートで、すべてのターミナルに同じ Python 環境を使用します。`python -m pip install -e ".[multi-party]"` で多人数会話用の依存関係をインストールします。`OPENAI_API_KEY` は各 DialBB スポークの環境変数またはリポジトリのルートの `.env` に設定します。必要に応じて、各サンプル設定の `model` を利用可能な OpenAI モデルに変更してください。

Windows では `sample_apps\multi_party_ja\test.bat` を実行すると、ハブと田中・鈴木の DialBB スポーク、山田として参加するための GUI が起動します。`--cli` で人間用の GUI をターミナルに切り替え、`--all-bots` で全員を DialBB にできます。`--port 5001` を指定するとハブのポートを変更できます。

個別に起動する場合は、ハブを最初に起動し、続いて田中と鈴木を起動します。各コマンドは別々のターミナルで実行します。

```sh
python -m dialbb.lib.multi_party.hub
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config1.yml 田中
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config2.yml 鈴木
```

田中は参加すると好きな食べ物の話題を切り出します。人間が山田として参加するには、もう一つのターミナルで以下のどちらかを実行します。

```sh
python -m dialbb.lib.multi_party.user_spoke_gui 山田
python -m dialbb.lib.multi_party.user_spoke 山田
```

GUI では **Join** で参加し、**Send** または Ctrl+Enter で発話を送ります。Enter は IME の入力に使えます。ターミナルでは Enter で参加し、発話を入力するたびに Enter で送信します。山田も DialBB にする場合は、人間用のスポークの代わりに次のコマンドを実行します。

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config3.yml 山田
```

ターミナルで起動したプロセスは Ctrl+C で終了します。人間用の GUI はウインドウを閉じると終了します。

### ハブと Socket.IO プロトコル

ハブは一つの会話を扱い、既定で `localhost:5000` で待ち受けます。待ち受け先は `--host` と `--port` で変更できます。各スポークは `--hub-url` で接続先を指定でき、既定値は `http://localhost:5000` です。たとえば、ハブに `--port 5001` を指定した場合は、各スポークの起動コマンドに `--hub-url http://localhost:5001` を追加します。

会話のイベントを送受信するには、接続後に `join` で参加登録します。名前は大文字・小文字を区別し、空白以外の文字を含む文字列で、参加中の名前と重複できません。名前の前後の空白は保持されます。同じ接続で同じ名前の `join` を再送すると成功しますが、参加通知は再配信されません。別名で参加するには、新しく接続します。

| ハブに送るイベント | データ | 動作 |
| --- | --- | --- |
| `join` | `{"speaker": "山田"}` | 接続を参加者として登録します。 |
| `utterance` | `{"speaker": "山田", "utterance": "ラーメンが好きです。"}` | 本文をそのまま配信します。発話者名は登録名と一致し、本文には空白以外の文字が必要です。 |

どちらも成功時は `{"ok": true}`、失敗時は `{"error": "..."}` を返します。接続を切ると退出になります。

| ハブが配信するイベント | データの項目 | 配信先 |
| --- | --- | --- |
| `participant_joined` | `speaker`、`participants` | 新規参加者を含む参加者全員 |
| `broadcast_utterance` | `speaker`、`utterance`、`participants` | 発話者を含む参加者全員 |
| `participant_left` | `speaker`、`participants` | 残りの参加者全員 |

`participants` はイベント発生時点の参加者名の一覧です。ハブには認証や履歴の再配信機能がありません。途中参加したスポークは、自分の参加通知以降のイベントを受信します。スポークの自動再接続は無効です。再参加するにはスポークを起動し直します。

### DialBB スポーク

DialBB スポークの位置引数は `config_file`、`my_name` の順です。ハブに接続すると、`initial=True`、`user_id: my_name`、空の `aux_data.participants` で DialBB セッションを初期化します。その後、ハブに参加登録し、初期発話があれば送信します。以降は一つのワーカーがイベントを順に処理し、同じセッションにリクエストを送ります。`aux_data.participants` には各イベントの参加者一覧を渡します。

| イベント | `user_id` | `user_utterance` |
| --- | --- | --- |
| 他の参加者の発話 | 発話者名 | 発話本文 |
| 参加 | 参加者名 | `(joined the conversaion)` |
| 退出 | 退出者名 | `(left the conversaion)` |
| スポークの沈黙タイマーの満了 | 空文字列 | `(silence)` |

`conversaion` という綴りはプロトコルの一部です。自分自身の参加通知も DialBB に渡します。自分の発話が配信されたときは対話処理を省略します。応答の `system_utterance` が空でなければ、`my_name` を発話者名としてハブに送信します。対話処理でエラーが起きると、そのスポークは切断します。

#### 沈黙タイマー

アプリケーション設定で `blocks` と同じ階層に `silence_timeout` を置き、秒単位で有限の非負数を指定します。省略または `0` で無効になります。参加後、自分の発話を含む発話の受信でタイマーをリセットします。参加・退出の通知では計測を継続します。指定時間が経過すると、最新の参加者一覧を添えて、そのスポーク内の DialBB に `(silence)` を渡します。キューにあるイベントを優先し、沈黙リクエストの処理が終わってから次の計測を始めます。タイマーはスポークごとに独立しているため、複数のスポークが同時に発話することがあります。

(llm_dialogue_multi_party)=

### `llm_dialogue` ブロックの `multi_party` 設定

アプリケーション設定の {ref}`llm_dialogue` ブロック直下に `multi_party` を置きます。マッピングを指定すると、空のマッピング `{}` でも多人数会話モードが有効になります。省略または `false` で無効になります。従来の形式で `true` を指定すると、オプションはブロック直下から読み込まれます。ブロックが参加者一覧から自分を識別できるように、`system_name` はスポークの `my_name` と完全に一致させます。

```yaml
language: ja
silence_timeout: 10
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
    prompt_template: prompt_template1.txt
    model: openai:gpt-4.1-mini
    multi_party:
      silence: 黙る
      turn_taking_strategy: after_all_other_speak
      required_participants: [田中, 山田]
```

| オプション | 既定値 | 動作 |
| --- | --- | --- |
| `required_participants` | `[]` | `first_system_utterance` を返すまでに参加が必要な参加者 ID の一覧です。空の一覧なら初期化時に初期発話を返します。初期発話を返すのはセッションにつき一度です。 |
| `turn_taking_strategy` | 未指定 | `after_all_other_speak` は現在参加中の自分以外の全員が少なくとも一度発話するまで待ち、他の参加者がいない場合も待機します。`wait_n_turns` は自分以外の発話が指定回数に達するまで待ち、同じ人の発話も一回ずつ数えます。未指定の場合は、参加・退出通知も含め、空でない入力があれば応答できます。 |
| `turns_to_wait` | `1` | `wait_n_turns` で待つ発話数です。正の整数を指定します。 |
| `silence` | 未指定 | この文字列に一致する応答を空の発話に変換します。比較の前に応答の前後の空白と `「」` を取り除きます。サンプルのプロンプトは、発話を見送る場合に `黙る` を返すようモデルに指示します。 |

どちらの発話順でも、直近の空でないシステム発話以降の発話を数え、参加・退出・沈黙の通知は発話数から除きます。参加・退出通知を受けた時点ですでに待機条件を満たしていれば、応答する場合があります。空の応答でもそれまでの発話数は保持されます。初期発話後に `aux_data.no_response_required` が真なら、応答を抑制します。それ以外では、沈黙リクエストを受けると通常の発話順を待たず、会話を再開するよう LLM に指示します。初期発話前は必須参加者がそろうまでの待機条件を優先します。

発話順の判定には現在の `aux_data.participants` を使い、この項目がなければ対話履歴の最新の一覧を使います。明示的な空の一覧は参加者がいないことを表します。LLM に渡す対話履歴では他の話者に `user_id`、自分に `system_name` を使います。現在のリクエストに `aux_data.participants` があれば、プロンプトテンプレートで `{participants}` として参照できます。

## 廃止された機能

### Snips Understander組み込みブロック

SnipsがPython3.9以上ではインストールが困難なため，ver. 0.9で廃止されました．代わりにLR-CRF Understander組み込みブロックを用いてください．

### Whitespace Tokenizer組み込みブロックおよびSudachi Tokenizer組み込みブロック

ver. 0.9で廃止されました．LR-CRF UnderstanderやChatGPT Understanderを使えばTokenizerブロックを使う必要はありません．

### Snips+STNサンプルアプリケーション

ver. 0.9で廃止されました．

### シンプルアプリケーション

ver. 2.0で廃止されました．

### 実験アプリケーション

ver. 2.0で廃止されました．
