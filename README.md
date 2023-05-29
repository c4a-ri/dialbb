# DialBB: 対話システム構築フレームワーク

ver.0.3.1

DialBBは対話システムを構築するためのフレームワークです．
非商用向けに公開しています．ライセンスの詳細は[ライセンス](LICENSE)をご覧ください．

DialBBのメインモジュールは，メソッド呼び出しまたはWeb API経由で，
ユーザ発話の入力をJSON形式で受けとり，システム発話をJSON形式で返します．

メインモジュールは，ブロックと呼ぶいくつかのサブモジュールを順に呼び出すことによって動作します．
各ブロックはJSON形式(pythonのdictのデータ)を受け取り，JSON形式のデータを返します．

各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

![dialbb-arch](docs/images/dialbb-arch.jpg)

詳細およびインストールの仕方は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．
最新バージョン以外のドキュメントは[リンク集](https://c4a-ri.github.io/dialbb/)にあります．

DialBBに関するご要望・ご質問は以下のところにお寄せください。

  - バグ報告など: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

  - 長期的な開発方針など：[GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)
  
  - 何でも：`dialbbあっとc4a.jp`

(c) C4A Research Institute, Inc.
