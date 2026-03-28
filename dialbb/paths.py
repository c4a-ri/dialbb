import os

# ダイアログアプリケーションのルート（このファイルがあるディレクトリ = dialbb/）
DIALBB_DIR = os.path.dirname(os.path.abspath(__file__))

# no_code モジュールのルート
NC_PATH = os.path.join(DIALBB_DIR, "no_code")

# no_code のサブディレクトリ
APP_DIR = os.path.join(NC_PATH, "app")
APP_FILE_PATH = os.path.join(APP_DIR, "scenario.xlsx")
TEMPLATE_DIR = os.path.join(NC_PATH, "templates")
DATA_DIR = os.path.join(NC_PATH, "data")

# サーバ用テンプレート/静的アセット
TEMPLATE_FOLDER = os.path.join(DIALBB_DIR, "server", "static", "new")
STATIC_ASSETS = os.path.join(TEMPLATE_FOLDER, "assets")

# GUI テキスト（no_code 用ローカライズファイル）
GUI_NC_TEXT = os.path.join(NC_PATH, "gui_nc_text.yml")
