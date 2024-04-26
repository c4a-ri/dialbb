# DialBB GUIエディタ

### 開発環境の構築
* vite + vue 3 + typescript 環境でビルドを行っています．  
  python, node.js も必要です.  

* （参考）開発環境  
  python 3.10.5  
  vite 5.0.8  
  vue 3.3.11  
  node.js 21.6.1  

* セットアップ  
  gui_editor/フォルダで
```
  $ npm install
```

* 動作確認  
```
  $ npm run dev
```

  ブラウザよりアクセス  
  http://localhost:5173/ 

* 本場用ビルド  
```
  $ npm run build
```
  dist/フォルダにリリース物が生成されます  
  

* ノードエディタの使い方  
  * ノードの追加：背景で右クリック > [Add Node]  
  * ノードの削除：ノードで右クリック > [Delete]  
  * コネクタの接続：右側ソケットを左クリック > 他ノードの左側ソケットへドラッグ  
  * ノードの挿入：単独ノードを接続ノードの間にドラッグすると結合する
  * ファイルに保存(JSON)：[Save]
  * ファイルから読み込み(JSON)：[Load]

-------  
### ツールを利用して知識記述Excelとノードエディタ用JSONに変換する方法
  リポジトリの **dialbb/no_code/Tools/** 配下の変換ツールを使用する
```sh
・知識記述Excel⇒JSON変換
    python knowledgeConverter2json.py sample-knowledge-ja.xlsx xxxx.json

・JSON⇒知識記述Excel変換
    python knowledgeConverter2excel.py xxxx.json sample-knowledge-ja.xlsx
```

