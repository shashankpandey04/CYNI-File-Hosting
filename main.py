from flask import Flask, request, jsonify, send_from_directory, render_template, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
import os
import uuid
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set app secret key
app.secret_key = os.getenv('SECRET_KEY', 'supersecret')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Fetch allowed origins and tokens
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_URI", "").split(",")]
valid_tokens = [token.strip() for token in os.getenv("FILE_AUTH_TOKEN", "").split(",")]

# Configure CORS
CORS(app, origins=allowed_origins, supports_credentials=True, methods=['POST', 'GET'], allow_headers=["Authorization", "Content-Type"])

# Constants
BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1')
UPLOAD_FOLDER = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Utility Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def verify_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    token = auth_header.split(" ")[1]
    return token.lower() in map(str.lower, valid_tokens)

# Disable cache
@app.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response

# Upload Route
@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.info("🚀 Upload endpoint hit")

    if not verify_token(request.headers.get("Authorization")):
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    if request.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File exceeds size limit"}), 413

    # Save file securely
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_name)

    try:
        file.save(file_path)
    except Exception as e:
        app.logger.error(f"File save error: {e}")
        return jsonify({"error": "File upload failed"}), 500

    file_url = f"{BASE_URL}/files/{unique_name}"
    return jsonify({"message": "File uploaded successfully", "url": file_url})

# Serve Uploaded Files
@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        app.logger.error(f"File retrieval error: {e}")
        return jsonify({"error": "File not found"}), 404

# Admin Login & Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == os.getenv('ADMIN_USERNAME') and password == os.getenv('ADMIN_PASSWORD'):
            login_user(User(1))
            return redirect('/admin')

    if current_user.is_authenticated:
        images = os.listdir(UPLOAD_FOLDER)
        return render_template('admin.html', images=images)

    return render_template('index.html')

# Logout Route
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect('/admin')

# Manage Uploaded Files
@app.route('/admin/manage', methods=['POST'])
@login_required
def manage():
    file_name = request.form.get('file_name')
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    if os.path.isfile(file_path):
        os.remove(file_path)
        app.logger.info(f"File deleted: {file_name}")
    else:
        app.logger.warning(f"Attempted to delete non-existing file: {file_name}")

    return redirect('/admin')

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Page not found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# Run Flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
