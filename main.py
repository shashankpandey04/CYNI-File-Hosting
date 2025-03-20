from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1')

UPLOAD_FOLDER = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    if request.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File exceeds size limit"}), 413

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(file_path)

    file_url = f"{BASE_URL}/files/{unique_name}"
    return jsonify({"message": "File uploaded successfully", "url": file_url})

@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
