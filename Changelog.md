# Changelog

## 0.3.1 (2023.5.xxx)

- STN Manager

  - もしリクエストのaux_dataのstop_dialogueの値がTrueなら、#final_abort状態に遷移する
  - リクエストの"aux_data"の"rewind"の値がTrueの場合、対話の状態を直前のものに戻し、対話文脈を戻す
  - デフォルト遷移の代わりに遷移しないことをオプションで選択可能に変更
  - リクエストの"aux_data"の"confidence"の値がコンフィギュレーションの"ask_repetition"の"confidence_threshold"の値以下の場合に、状態遷移をおこなわず、"ask_repetition"の"utterance"の値をシステム発話とする。
  - 入力がlong silenceの場合に，コンフィギュレーションのreaction_to_silenceに応じて動作を変更する
  - 組み込みシナリオ関数 _confidence_is_low, _is_long_silenceを実装
  - prep stateからinitialではないstateに遷移可能
  - condition functionの引数が0でも良いように変更

## 0.3.0 (2023.4.13)

- 組み込みの単語分割ブロッククラスを追加。それに伴い、SNIPS Understanderの入力が文字列からトークン列に変更（後方互換性なし）

## 0.2.1 (2022.12.1)

- ドキュメントの間違いを修正(5.2.2)

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

