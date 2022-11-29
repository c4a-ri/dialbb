# DialBB: 対話システム構築フレームワーク

ver 0.1.1

DialBBは対話システムを構築するためのフレームワークで，非商用向けに公開しています．ライセンスの詳細は[ライセンス](LICENSE)をご覧ください．


DialBBのメインモジュールは，メソッド呼び出しまたはWeb API経由で，
ユーザ発話の入力をJSON形式で受けとり，システム発話をJSON形式で返します．

メインモジュールは，ブロックと呼ぶいくつかのサブモジュールを順に呼び出すことによって動作します．
各ブロックはJSON形式(pythonのdictのデータ)を受け取り，JSON形式のデータを返します．

各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

![dialbb-arch](docs/images/dialbb-arch.jpg)

詳細は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．

本バージョンが最新でない場合，本バージョンのドキュメントは(docs/document-ja/build/latex/dialbb.pdf)にあります．


(c) C4A Research Institute, Inc.
