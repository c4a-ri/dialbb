# DialBB GUI シナリオ・エディタ

### 開発環境の構築
* vite + vue 3 + typescript 環境でビルドを行っています．  
  python, node.js も必要です.  

* （参考）開発環境  
  python 3.10.5  (3.8.10でも動作確認済み)  
  vite 5.0.8  
  vue 3.3.11  
  node.js 21.6.1  

* セットアップ  
  gui_editor/フォルダで
```
npm install
```

* 動作確認  
```
npm run dev
```

  ブラウザよりアクセス  
  http://localhost:5173/ 

* 本番用ビルド  
```
npm run build
```
  dialbb/no_code/gui_editor/フォルダにリリース物が生成されます  
  

### シナリオ・エディタの起動方法  
dialbb/no_code/README を参照.  


### シナリオ・エディタの使い方  

#### ・概要

シナリオを[systemノード]と[userノード]として扱います、それぞれのノードを[コネクタ]で接続することでsystem：userを関連付けます。

<img src="images/editor-main.jpg" width="50%">

#### ・ノードの追加
背景で右クリック > [systemノード]か[userノード]を選択すると新規追加されます 

<img src="images/add-node.jpg" width="30%">


#### ・ノードの削除
ノードの上で右クリック > [Delete] を選択すると削除されます  

<img src="images/del-set.jpg" width="30%">

#### ・ノード項目の入力
ノードの上で右クリック > [Edit] を選択すると入力ダイアログが表示されます  

<img src="images/sys-setting.jpg" width="30%">　<img src="images/user-setting.jpg" width="30%">

#### ・コネクタの接続・削除
ノードのoutputソケットを左クリック > 他ノードのinputソケットへドラッグして接続します  
削除はinputソケットを摘まんで離すか、コネクター上で右クリック > [Delete] を選択します。

<img src="images/editor-connection.jpg" width="30%">　<img src="images/editor-conn-del.jpg" width="30%">


#### ・ファイルに保存(Excel)
上部の[Save]ボタンをクリックします、ノードデータをシナリオExcelに書き込みます。（保存しないでエディタサーバを停止した場合はデータが失われます）

-------  

