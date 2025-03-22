from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, json
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response

BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1')

UPLOAD_FOLDER = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    valid_tokens = [token.strip() for token in os.getenv("FILE_AUTH_TOKEN", "").split(",")]

    print(f"Received auth header: {auth_header}")
    print(f"Valid tokens: {valid_tokens}")

    if token not in valid_tokens:
        return jsonify({"error": "Unauthorized"}), 401

    if token.lower() not in map(str.lower, valid_tokens):
        return jsonify({"error": "Unauthorized"}), 401

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

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        if current_user.is_authenticated:
            images = os.listdir(UPLOAD_FOLDER)
            return render_template('admin.html', images = images)
        return render_template('index.html')

    username = request.form.get('username')
    password = request.form.get('password')

    if username == os.getenv('ADMIN_USERNAME') and password == os.getenv('ADMIN_PASSWORD'):
        user = User(1)
        login_user(user)
        images = os.listdir(UPLOAD_FOLDER)
        return render_template('admin.html', images=images)
    
    return render_template('index.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return render_template('index.html')

@app.route('/admin/manage', methods=['POST'])
@login_required
def manage():
    file_name = request.form.get('file_name')
    os.remove(os.path.join(UPLOAD_FOLDER, file_name))
    return redirect('/admin')

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Page not found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
