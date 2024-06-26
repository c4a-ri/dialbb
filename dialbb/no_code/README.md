# DialBB ノーコード

------

## 実装状況
ver0.1.6
* 実装機能 (2024.6.26)
  * コンフィギュレーションGUIの画面制御
  * Scenario編集機能
  * Knowledge編集機能
  * GUIシナリオエディタの起動／停止
  * DialBBサーバの起動／停止
  * インストールパッケージ化
  * コマンド起動
  * Configの編集
  * ロードしているアプリ名の表示
  * OPENAI_API_KEYの設定
  * templatesの置き場所をdialbb/no_code/tempates/に変更
  * トップレベルにrun_server.pyを追加
  * dialbb-server起動コマンド追加
  * undo/redo機能
* 実装予定
  * アプリ・アイコンはMacで画像NGのため一旦削除

------

## 動作確認環境
* OS: Windows 11 Pro 64bit
* Python for windows 3.10.5 and 3.8.10
* Google Chrome バージョン：123.0.6312.86
* Microsoft Edge バージョン：123.0.2420.65

------

## インストール方法
* whlファイルをdistフォルダからダウンロードします  
  [dist](https://github.com/c4a-ri/dialbb/tree/dev-v2/dist)：例）dialbb_nc-x.x.x-py3-none-any.whl  
* パッケージのインストール
```sh
> pip install <ダウンロードしたwhlファイルの名前> 
```

------

## DialBB ノーコードの起動コマンド
```sh
> dialbb-nc
```

------

## GUI操作方法
### コンフィグレーションGUIの使い方  


### シナリオ エディタの使い方  
[ここ](../builtin_blocks/stn_management/gui_editor/README-ja.md#シナリオエディタの使い方)を参照

