# Appendix

## フロントエンド

DialBBには、Web APIにアクセスするための、2種類のサンプルフロントエンドが付属しています。

### シンプルなフロントエンド

以下でアクセスできます。

```
http://<ホスト>:<ポート番号>
```

システム発話とユーザ発話を吹き出しで表示します。

`aux_data`の送信はできません。また、レスポンスに含まれるシステム発話以外の情報は表示されません。

### デバッグ用フロントエンド

以下でアクセスできます。

```
http://<ホスト>:<ポート番号>/test
```

システム発話とユーザ発話をリスト型式で表示します。

`aux_data`の送信ができます。また、レスポンスに含まれる`aux_data`も表示されます。



## 廃止された機能

### Snips Understander組み込みブロック

SnipsがPython3.9以上ではインストールが困難なため，ver. 0.9で廃止されました．代わりにLR-CRF Understander組み込みブロックを用いてください．

### Whitespace Tokenizer組み込みブロックおよびSudachi Tokenizer組み込みブロック

ver. 0.9で廃止されました．LR-CRF UnderstanderやChatGPT Understanderを使えばTokenizerブロックを使う必要はありません．

### Snips+STNサンプルアプリケーション

ver. 0.9で廃止されました．

