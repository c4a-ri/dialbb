# DialBBフロントエンド

## 説明
    
    DialBBのフロントエンドのソースコードです．
    
    vite + vue 3 + typescript 環境でビルドを行っています．
    
    [vue.js](https://v3.ja.vuejs.org/)

    [vite](https://ja.vitejs.dev/)

    [typescript](https://www.typescriptlang.org/)

    UIツールとして bootstrap5 と bootstrap5 icon を使用しています．

    [bootstrap 5](https://getbootstrap.com/)

    このソースコードは `script setup`という vue3 composition APIの新しい形式で書かれています．

    詳しくは以下を参照してください．

    [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup).

## セットアップ

    node.jsをインストールしてください．

    [node.js](https://nodejs.org/ja/)

    frontendフォルダにて

    ```
    npm install
    ```

    にて必要ライブラリをインストールします．

    ```
    npm run build
    ```

    にてソースコードをビルドし，`/main/static/new/` 以下にビルドされたhtml, js, css を配置します．



## ソースコードの説明

    - src/index.html エントリーポイントのhtmlです．
    - src/main.ts おおもとのtsファイルです．
    - src/App.vue vue 最初に呼び出されるvueコンポーネントです．．
    - src/components/DialogMain.vue 対話の全体を司るコンポーネントです．
    - src/components/SystemUtterance.vue システム発話の表示をしているコンポーネントです．
    - src/components/UserUtterance.vue ユーザー発話の表示をしているコンポーネントです．

## 操作

htmlを開くと，上部にテキストボックスがあり，「ユーザー名」と表示されています．

ユーザー名を入力し，「対話開始」ボタンをクリックします．

そうすると，システムから返答がありますので，画面下のテキストボックスに発話文を入力してください．

発話文が表示され，それに対するシステム応答が表示されます．

この繰り返しで動作をします．

発話が画面いっぱいになると，自動的に上部にスクロールし最近の発話を表示します．



