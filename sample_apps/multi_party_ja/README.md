# DialBB 多人数会話サンプル

`multi-party` ブランチのハブと参加者（spoke）をもとに、田中・鈴木・山田の
3 人で会話します。田中・鈴木は DialBB、山田は人間または DialBB です。
対話生成には `llm_dialogue` ブロック（`LLMDialogue`）を使用します。
ハブは参加者の登録・退出・発話を随時配信します。
田中と山田が参加すると、田中の「好きな食べ物について話しましょう」で始まります。
鈴木はその前後どちらでも参加できます。

## インストール

Python 3.11 以降を使い、リポジトリのルートで実行してください。

```sh
python -m pip install -e ".[multi-party]"
```

すでに DialBB をインストールしている場合は、追加依存だけでも構いません。

```sh
python -m pip install -r sample_apps/multi_party_ja/requirements.txt
```

以下の起動コマンドもすべてリポジトリのルートで実行します。
各ターミナルで同じ Python 環境を使用してください。

## ハブの起動

```sh
python -m dialbb.lib.multi_party.hub
```

## 田中・鈴木の起動

それぞれ別のターミナルを開き、API キーを設定します。
PowerShell では次のように設定します。

```powershell
$env:OPENAI_API_KEY = "<OpenAI API Key>"
```

bash/zsh では `export OPENAI_API_KEY="<OpenAI API Key>"` を使います。
ルートの `.env` に `OPENAI_API_KEY=...` を記載する方法も使えます。

田中のターミナル:

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config1.yml 田中
```

鈴木のターミナル:

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config2.yml 鈴木
```

## 山田として人間が参加

別のターミナルで起動し、Join ボタンを押して参加します。
入力欄に発話を入れ、Send または Ctrl+Enter で送信します。
Enter は日本語 IME の変換確定に使えるよう、送信には割り当てていません。
GUI は DialBB の依存に含まれる PySide6 の入力欄を使用します。

```sh
python -m dialbb.lib.multi_party.user_spoke_gui 山田
```

ターミナルから参加する場合は、次のコマンドを使い、Enter を押して参加します。

```sh
python -m dialbb.lib.multi_party.user_spoke 山田
```

## 3 人とも DialBB にする場合

人間用の参加者の代わりに、API キーを設定したターミナルで起動します。

```sh
python -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_ja/config3.yml 山田
```

## 設定と終了

- `model` で使用するモデルを変更できます。サンプルは `gpt-5.6-luna` を使用します。
  他のプロバイダーを使う場合は、対応する API キーと LangChain 連携パッケージを設定してください。
- 各設定の `prompt_template` がペルソナや発話生成の指示を指定します。
- `multi_party` の下に `silence`、`turn_taking_strategy`、`turns_to_wait`、
  `required_participants` を設定します。
  `silence` は発話しない場合のモデルの回答です。
- `turn_taking_strategy: after_all_other_speak` は現在参加している他の全員の発話を待ちます。
  `wait_n_turns` は `turns_to_wait` 回の発話を待ちます。参加・退出の通知は発話回数に含めません。
- 設定ファイルのトップレベルの `silence_timeout`（秒）を各 `dialbb_spoke` が使います。
  指定時間、誰の発話も受信しなければ、`user_id: ""`、`user_utterance: "(silence)"`
  を DialBB に送ります。`aux_data.participants` はその時点の参加者一覧です。
  自分の発話の配信を受信した場合もタイマーをリセットし、参加・退出ではリセットしません。
  未指定または `0` で無効になります。
- 沈黙のリクエストは、通常の発話順の待機条件を一度だけ外して LLM に会話の再開を依頼します。
  `required_participants` がそろう前は初期発話の待機を優先します。
  DialBB の処理中にリクエストを重ねず、沈黙への応答後は次の通知まで指定時間待ちます。
  各スポークが独立に判定するため、同時発話を避けやすいようにサンプルでは
  田中10秒・鈴木12秒・山田14秒を指定しています。
- 各スポークには処理中・待機中の状態が表示されます。
  DialBB の処理がエラーで終了した場合はハブから切断し、退出を他の参加者へ知らせます。
- ハブのポートを変える場合は `--port 5001` を指定し、各参加者に
  `--hub-url http://localhost:5001` を指定します。
- 終了は各ターミナルで Ctrl+C（GUI はウインドウを閉じる）。
  ハブが動作していれば、参加者は途中で退出・再参加できます。

## 初期化と参加者情報

`dialbb_spoke` はハブに接続するとすぐに DialBB セッションを初期化します。
`multi_party.required_participants` が指定されている場合は、指定された user ID が
現在の参加者一覧にすべて含まれるまで待ち、そのセッションで一度だけ
`first_system_utterance` を返します。未指定の場合は初期化時に返します。

```yaml
silence_timeout: 10
blocks:
  - name: llm_dialogue
    # ... other block settings ...
    multi_party:
      silence: 黙る
      turn_taking_strategy: after_all_other_speak
      required_participants:
        - 田中
        - 山田
```

`silence_timeout` はブロック設定や `multi_party` の中ではなく、`blocks` と同じ階層に置きます。

ハブ用の参加者設定ファイルは不要です。参加者は任意の名前で登録できます。
同じ名前の同時登録はできません。

参加すると、その user ID と `"(joined the conversaion)"`、退出すると
その user ID と `"(left the conversaion)"` を各 DialBB に送ります。
新しく参加する DialBB は自分自身の参加通知も受け取ります。
発話を送る場合も含め、`aux_data.participants` はそのイベント発生時点の
参加者の user ID のリストになります。退出通知のリストには退出者を含みません。

## Windows のテスト用バッチ

API キーを環境変数またはルートの `.env` に設定して実行します。

```bat
sample_apps\multi_party_ja\test.bat
```

ハブ・田中・鈴木・山田の4つのコンソールウインドウが開きます。
標準では山田のコンソールに加えて、人間用の GUI ウインドウが開きます。
日本語を入力する場合は GUI の入力欄を使ってください。
Join を押して参加し、Send または Ctrl+Enter で送信します。
山田のコンソールはログ表示用です。

従来の CLI を使う場合:

```bat
sample_apps\multi_party_ja\test.bat --cli
```

CLI では山田のコンソールで Enter を押すと参加します。

3人とも DialBB にする場合、またはポートを変更する場合:

```bat
sample_apps\multi_party_ja\test.bat --all-bots
sample_apps\multi_party_ja\test.bat --port 5001
```

沈黙の待ち時間は各設定ファイルの `silence_timeout` で変更します。

バッチはルートの `.venv\Scripts\python.exe` があれば使用し、なければ `python` を使います。
別の Python を使う場合は `DIALBB_PYTHON` に実行ファイルのパスを設定してください。
ハブの起動を確認してから各スポークを開きます。

## bat / sh による起動

起動制御は `test.bat` と `test.sh` で行い、Python のランチャースクリプトは使いません。
DialBB 本体の実行には引き続き Python が必要です。
`test.bat` はハブの起動確認に `curl.exe`（最近の Windows に付属）を使います。

Linux/macOS では、`curl` をインストールして次を実行します。

```sh
sh sample_apps/multi_party_ja/test.sh
sh sample_apps/multi_party_ja/test.sh --cli
sh sample_apps/multi_party_ja/test.sh --all-bots
sh sample_apps/multi_party_ja/test.sh --port 5001
```

sh 版はハブとボットをバックグラウンドで起動し、人間用の GUI または CLI を
フォアグラウンドで実行します。ハブとボットのログは起動時に表示する一時ディレクトリに保存します。
人間用の参加者を終了するか Ctrl+C を押すと、このスクリプトが起動したプロセスを停止します。
全員ボットの場合も Ctrl+C で終了します。ログは終了後も残ります。

sh 版は `.venv/bin/python` があれば使用し、なければ `python3` を使います。
`DIALBB_PYTHON` で実行ファイルを指定することもできます。
bat / sh ともに、任意の作業ディレクトリから実行できます。
