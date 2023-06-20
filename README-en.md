# DialBB: A Framework for Building Dialogue Systems


ver.0.5.0

DialBB is a framework for building dialogue systems.

This software is released for non-public use and commercial use. For details of the license, please see [License](LICENSE-en).

The main module of DialBB application recives a user utterance input in JSON format via method calls or via the Web API returns a system utterance in JSON format.


メインモジュールは，ブロックと呼ぶいくつかのサブモジュールを順に呼び出すことによって動作します．
各ブロックはJSON形式(pythonのdictのデータ)を受け取り，JSON形式のデータを返します．

各ブロックのクラスや入出力仕様はアプリケーション毎のコンフィギュレーションファイルで規定します．

![dialbb-arch-en](docs/images/dialbb-arch-en.jpg)

詳細およびインストールの仕方は[ドキュメント](https://c4a-ri.github.io/dialbb/document-ja/build/html/)を参照して下さい．
最新バージョン以外のドキュメントは[リンク集](https://c4a-ri.github.io/dialbb/)にあります．

DialBBに関するご要望・ご質問・バグ報告は以下のところに気軽にお寄せください．些細なことや漠然とした質問でも構いません．

  - バグ報告・ドキュメントの不備指摘など: [GitHub Issues](https://github.com/c4a-ri/dialbb/issues)

  - 長期的な開発方針など：[GitHub Discussions](https://github.com/c4a-ri/dialbb/discussions)
  
  - 何でも：`dialbbあっとc4a.jp`

(c) C4A Research Institute, Inc.




The main module works by calling several submodules, called blocks, in sequence.
Each block takes JSON format (data in python dict) and returns the data in JSON format.
The class and input/output specifications of each block are specified in the configuration file for
each application.
Please refer to the documentation for details and installation
instructions. Documentation for other than the latest version
can be found in the Links section.
Please feel free to send your requests, questions, and bug reports about DialBB to the following
address. Even if it is a trivial or vague question, please feel free to send it to us at the following
address.
Report bugs, point out missing documentation, etc.: GitHub Issues
Long-term development policy, etc.
︓GitHub Discussions ︓ anything ︓
dialbb at c4a.jp
(c) C4A Research Institute, Inc.DialBB: A Framework for Building
Dialogue Systems
ver.0.4.0
DialBB is a framework for building dialogue systems.
This software is released for non-public use and commercial use. For details of the license, please see
License.
The DialBB main module can be accessed via method calls or via the Web API using the
Receives input of user speech in JSON format and returns system speech in JSON format.
The main module works by calling several submodules, called blocks, in sequence.
Each block takes JSON format (data in python dict) and returns the data in JSON format.
The class and input/output specifications of each block are specified in the configuration file for
each application.
Please refer to the documentation for details and installation
instructions. Documentation for other than the latest version
can be found in the Links section.
Please feel free to send your requests, questions, and bug reports about DialBB to the following
address. Even if it is a trivial or vague question, please feel free to send it to us at the following
address.
Report bugs, point out missing documentation, etc.: GitHub Issues
Long-term development policy, etc.
︓GitHub Discussions ︓ anything ︓
dialbb at c4a.jp
(c) C4A Research Institute, Inc.
