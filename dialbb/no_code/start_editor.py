from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os

DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui_editor')
print(f'template_folder={DOC_ROOT}')

app = Flask(__name__,  template_folder=DOC_ROOT, 
            static_folder=os.path.join(DOC_ROOT, 'static'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    print(request)
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(DOC_ROOT, 'static/data/', filename))
        return 'File successfully uploaded'


if __name__ == '__main__':
    app.debug = True
    app.run(host='localhost')
