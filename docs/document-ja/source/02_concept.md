# DialBBの概要

{ref}`intro`に書いたように，DialBBは対話システムを作るためのフレームワークです．

フレームワークとは，それ単体でアプリケーションとして成立はしないが，データや追加のプログラムを与えることでアプリケーションを作成するものです．

DialBBのアプリケーションは，ブロックと呼ぶモジュールが順に処理を行うことで，ユーザからの入力発話に対するシステム発話を作成し返します．以下に基本的なアーキテクチャを示します．

![dialbb-arch](../../images/dialbb-arch.jpg)

メインモジュールは，対話の各ターンで入力されたデータ（ユーザ発話を含みます）を各ブロックに順次処理させることにより，システム発話を作成して返します．このデータのことをpayloadと呼びます．各ブロックは，payloadの要素のいくつかを受け取り，辞書形式のデータを返します．返されたデータはpayloadに追加されます．すでに同じキーを持つ要素がpayloadにある場合は上書きされます．

どのようなブロックを使うかは，コンフィギュレーションファイルで設定します．ブロックは，あらかじめDialBBが用意しているブロック（組み込みブロック）でもアプリケーション開発者が作成するブロックでも構いません．

メインモジュールが各ブロックにどのようなデータを渡し，どのようなデータを受け取るかもコンフィギュレーションファイルで指定します．



詳細は「{ref}`framework`」で説明します．
