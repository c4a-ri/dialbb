# DialBBノーコードツール ドキュメント



## はじめに

本ドキュメントはDialBBのノーコードツール

## 動作環境

Windows11、MacOSで動作します。

## インストール

### Pythonのインストール

- Windows 11

  - 以下の手順でPythonをインストールします。

    - ブラウザのアドレスバーに https://www.python.org/downloads/windows/ を打ち込んでEnterキーを押します。
    - 表示されている中から以下の部分を探します。3.10.11である必要があります。

    ![python-install-win-ja](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\python-download-win.png)

    - 64bit OSの場合は、[Windows installer (64-bit)](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)を、32bit OSの場合は[Windows installer (32 -bit)](https://www.python.org/ftp/python/3.10.11/python-3.10.11.exe)をクリックします。

    - ダウンロードフォルダに `python-3.10.11-amd64.exe`または`python-3.10.11-amd32.exe`というファイルができるので、ダブルクリックします。

    - 以下の画面が現れます。

      ![python-setup-win](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\python-setup-win.png)

      - Add python.exe to PATHに**チェックを入れてから**Install Nowをクリックします。

        ![python-setup-win-path](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\python-setup-win-path.png)

      - Pythonがインストールされます。

### DialBBのインストール

- 以下の要領でwhlファイルをダウンロードします。

  - ブラウザでのアドレスバーに https://github.com/c4a-ri/dialbb/tree/dev-v1.0b/dist を打ち込んでEnterキーを押します。

  - dialbb_nc-0.1.5-py3-none-any.whl をクリックします。0.1.5のところは数字が違う可能性があります。

  - 遷移したページの右側の下向き矢印をクリックします。

    ![github-download](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\github-download.png)

  - ダウンロードフォルダにwhlファイルがダウンロードされます。

- 以下の要領でdialbbをインストールします。

  - 検索窓に"cmd"と入力して、Enterキーを押します。

    ![find-cmd](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\find-cmd.png)

  - コマンドプロンプトが現れます。

    ![cmd-started-ja](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\cmd-started-ja.png)

  - 以下のコマンドを打ち込んでEnterキーを押します。

    - pip install Downloads\dialbb_nc-0.1.5-py3-none-any.whl 

      ![pip-install-win-ja](C:\Users\nakano\system11\dialbb\dialbb-next\docs\no-code-tools\images\pip-install-win-ja.png)

      \は円マーク(￥の半角)の場合があります。

      \の右側はダウンロードしたファイルの名前です。

  

## 起動

## アプリケーションの作成・読み込み・保存

## シナリオエディタ

## 言語理解用知識の編集

## コンフィギュレーション

