# Changelog

## 0.9.0 

- LR-CRF Understanderブロックを追加

- LR-CRF Understanderブロックを用いたサンプルアプリケーション(simple_ja, simple_en)を追加

- Snips Understanderを用いたサンプルアプリケーション(network_ja, network_en)を削除

## 0.8.0 

- OpenAI API KEYをセットする環境変数のデフォルトをOPENAI_API_KEYに変更

- STN Manager組み込みブロック

  - システム発話の中で特集変数の参照や関数呼び出しを行えるように変更

  - LLM (ChatGPT)を利用した組み込み生成と組み込み条件関数を実装
  
  - 組み込みシナリオ関数のシンタクスシュガーを用意

## 0.7.0 (2024.3.6)

- 日本語実験アプリケーションがChatGPT言語理解ブロックを利用するように変更

- 英語実験アプリケーションを追加

- ChatGPT言語理解ブロックを追加

- ChatGP対話ブロックを変更 (後方互換性なし)

## 0.6.2 (2024.2.29)

- ドキュメント内のバグをfix

## 0.6.1 (2023.12.22)

- STN Manager ブロックがnlu_result=Noneを受け取ったときのバグをfix

- OpenAIのライブラリのアップデートに対応（1.3.5）

## 0.6.0 (2023.8.17)

- spaCy/GiNZAを用いた固有表現抽出の組み込みブロックを追加
  
  - sample_apps/lab_app_ja に利用例を追加

- ChatGPT組み込みブロックを追加

- requirements.txtをサンプルアプリ毎に用意

- dialbb/util/send_test_request.pyをdialbb/util/send_test_requests.pyにrename

- run_server.pyをDIALBB_HOME以外のディレクトリで起動しても良いようにした．

- sample_apps/lab_app_ja/README.mdの内容をドキュメントに統合

## 0.5.1 (2023.8.13)

- STN Manager組み込みブロック

  - \#で始まる変数を具体化できなかった時に空文字列を返すようになっていなかったバグをfix
  
## 0.5.0 (2023.6.29)

- STN Manager組み込みブロック

  - subdialogueの導入
  
  - skip stateの導入
  
  - 確認発話要求の導入
  
  - リアクションの導入


## 0.4.0 (2023.6.4)

- クラスAPIの場合，requestは破壊的に操作しない

- STN Manager組み込みブロック

  - もしリクエストのaux_dataのstop_dialogueの値がTrueなら，#final_abort状態に遷移する

  - リクエストの"aux_data"の"rewind"の値がTrueの場合，対話の状態を直前のものに戻し，対話文脈を戻す

  - デフォルト遷移の代わりに遷移しないことをオプションで選択可能に変更

  - リクエストの"aux_data"の"confidence"の値がコンフィギュレーションの"ask_repetition"の"confidence_threshold"の値以下の場合に，状態遷移をおこなわず，"ask_repetition"の"utterance"の値をシステム発話とする．

  - 入力がlong silenceの場合に，コンフィギュレーションのreaction_to_silenceに応じて動作を変更する

  - 組み込みシナリオ関数 _confidence_is_low, _is_long_silenceを実装

  - prep stateからinitialではないstateに遷移可能

  - 文脈情報にaux_dataを自動的に付加

  - 直前のシステム発話を文脈情報に付加

  - condition functionの引数が0の場合にエラーになるバグを修正

  
## 0.3.0 (2023.4.13)

- 組み込みの単語分割ブロッククラスを追加．それに伴い，SNIPS Understanderの入力が文字列からトークン列に変更（後方互換性なし）

## 0.2.1 (2022.12.1)

- ドキュメントの間違いを修正 (5.2.2)

## 0.2.0 (2022.12.1)

- AbstractBlockのインタフェースの変更（後方互換性なし）

  - processメソッドの引数の変更を変更
  
- デフォルト言語を日本語に

- STN Managerブロックの変更

  - シナリオグラフの書き出し
  
  - 準備状態の導入
  
- Google Sheetsが利用できるように変更

- テストシナリオのフォーマットを変更（後方互換性なし）

- SNIPS Understander用知識記述のカラム名変更（後方互換性なし）

- SNIPS Understanderのn-best出力に対応

## 0.1 (2022.8.9)

initial public version

