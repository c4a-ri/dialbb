import argparse
import zipfile
import dialbb
import os

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("editor_gui_zip_file", help="Editor GUI zip file")
    args = parser.parse_args()

    editor_dir = os.path.join(os.path.dirname(dialbb.__file__), 'no_code/gui_editor')

    with zipfile.ZipFile(args.editor_gui_zip_file) as zf:
        zf.extractall(editor_dir)

    print(f"Scenario editor GUI has been installed at: {editor_dir}.")
