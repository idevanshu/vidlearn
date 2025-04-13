import os
import json
import logging
from flask import Flask, request, jsonify, send_file, send_from_directory, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Video
from main import generate_video  # Video generation function (defined in main.py)
from quiz import generate_quiz
from progress import set_progress, get_progress  # Shared progress module
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

# -------------------- Configuration --------------------
# Set the path to your React build directory.
# Ensure you have run: npm run build (in your React project)
FRONTEND_BUILD = os.path.join(os.getcwd(), "frontend", "build")

# Initialize Flask with the React build as the static and template folder.
app = Flask(__name__, static_folder=FRONTEND_BUILD, template_folder=FRONTEND_BUILD)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your-secret-key-change-me")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///site.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# Folders for file uploads and output videos
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
OUTPUT_FOLDER = os.path.join(os.getcwd(), "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------- Flask-Login Setup --------------------
login_manager = LoginManager(app)
# Set the login view if a protected endpoint is hit.
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Note: SQLAlchemy’s .get() is considered legacy—update for SQLAlchemy 2.0 if needed.
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# -------------------- Serve React Frontend --------------------
# We do not require login to load the React app. Let the client handle route protection.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    # Serve any static file from the build folder if it exists
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise, serve index.html so React Router can handle client-side routing.
    return send_from_directory(app.static_folder, 'index.html')

# -------------------- Authentication Endpoints --------------------
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json or request.form
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')  # Extract email

    if not username or not password or not email:
        return jsonify({"error": "Username, email, and password are required."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Signup successful, please log in."}), 200


@app.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return jsonify({"success": True, "message": "Already logged in."}), 200

    data = request.json or request.form
    identifier = data.get('username') 
    password = data.get('password')
    
    # Determine whether to search by email or username
    if identifier and "@" in identifier:
        user = User.query.filter_by(email=identifier).first()
    else:
        user = User.query.filter_by(username=identifier).first()
    
    if user and check_password_hash(user.password, password):
        login_user(user)
        return jsonify({"success": True, "message": "Logged in successfully."}), 200
    else:
        return jsonify({"error": "Invalid credentials."}), 400


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200

# -------------------- Video Generation & Quiz Endpoints (Protected) --------------------
@app.route('/generate-video', methods=['POST'])
@login_required
def generate_video_endpoint():
    try:
        prompt = request.form.get('prompt', '').strip()
        if not prompt:
            set_progress({"step": "Error", "message": "Prompt is required."}, user_id=current_user.id)
            return jsonify({'success': False, 'error': 'Prompt is required.', 'step': 'Initial validation'}), 400

        # Handle optional file attachment.
        attachment = request.files.get('attachment')
        attachment_filename = None
        if attachment:
            filename = secure_filename(attachment.filename)
            folder = os.path.join(app.config['UPLOAD_FOLDER'], "pdf") \
                if filename.lower().endswith('.pdf') else os.path.join(app.config['UPLOAD_FOLDER'], "images")
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            attachment.save(filepath)
            attachment_filename = filename
            prompt += f" (See attached file: {filename})"

        # Prepare user's output folder.
        user_output_folder = os.path.join(OUTPUT_FOLDER, f"{current_user.username}_output")
        os.makedirs(user_output_folder, exist_ok=True)

        words = prompt.split()
        filename_base = "_".join(words[:10])
        raw_filename = f"{current_user.id}_{filename_base}.mp4"
        computed_filename = secure_filename(raw_filename)
        output_file_path = os.path.join(user_output_folder, computed_filename)

        app.logger.info("Starting video generation for prompt: %s", prompt)
        set_progress({"step": "Initializing", "message": "Starting video generation"}, user_id=current_user.id)
        success = generate_video(prompt, computed_filename, current_user.username)

        if success and os.path.exists(output_file_path):
            app.logger.info("Video generated successfully. File: %s", output_file_path)
            try:
                with open("scripts.json", "r", encoding="utf-8") as f:
                    script = json.load(f)
            except Exception as e:
                app.logger.error("Error reading scripts.json: %s", str(e))
                set_progress({"step": "Error", "message": f"Error reading scripts.json: {e}"}, user_id=current_user.id)
                return jsonify({'success': False, 'error': 'Error reading generated script file.', 'step': 'Script reading'}), 500

            # Save the new video record into the database.
            new_video = Video(
                user_id=current_user.id,
                filename=computed_filename,
                filepath=output_file_path,
                prompt_text=prompt,
                attachment_filename=attachment_filename
            )
            db.session.add(new_video)
            db.session.commit()

            return jsonify({
                'success': True,
                'filename': computed_filename,
                'script': script,
                'step': 'Completed'
            }), 200
        else:
            app.logger.error("Video generation failed or output file not found.")
            set_progress({"step": "Error", "message": "Video generation failed or output file not found."}, user_id=current_user.id)
            return jsonify({'success': False, 'error': 'Video generation failed.', 'step': 'Video generation'}), 500

    except Exception as e:
        app.logger.exception("Exception during video generation:")
        set_progress({"step": "Error", "message": str(e)}, user_id=current_user.id)
        return jsonify({'success': False, 'error': str(e), 'step': 'Unexpected error'}), 500

@app.route('/download-video', methods=['GET'])
@login_required
def download_video():
    filename = request.args.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'Filename query parameter is required.'}), 400

    user_output_folder = os.path.join(OUTPUT_FOLDER, f"{current_user.username}_output")
    output_path = os.path.join(user_output_folder, filename)

    if os.path.exists(output_path):
        app.logger.info("Download request for file: %s", output_path)
        return send_file(output_path, as_attachment=True)
    else:
        app.logger.error("File not found: %s", output_path)
        return jsonify({'error': 'File not found.'}), 404

@app.route('/generate-quiz', methods=['POST'])
@login_required
def generate_quiz_endpoint():
    try:
        data = request.get_json() or {}
        script = data.get('script')
        if not script:
            set_progress({"step": "Error", "message": "Script is required for quiz generation."}, user_id=current_user.id)
            return jsonify({
                'success': False,
                'error': 'Script is required to generate quiz.',
                'step': 'Initial validation'
            }), 400

        app.logger.info("Starting quiz generation based on the script.")
        quiz = generate_quiz(script)
        if quiz:
            app.logger.info("Quiz generation successful.")
            return jsonify({'success': True, 'quiz': quiz, 'step': 'Completed'}), 200
        else:
            app.logger.error("Quiz generation failed.")
            set_progress({"step": "Error", "message": "Quiz generation failed."}, user_id=current_user.id)
            return jsonify({'success': False, 'error': 'Quiz generation failed.', 'step': 'Quiz generation'}), 500

    except Exception as e:
        app.logger.exception("Exception during quiz generation:")
        set_progress({"step": "Error", "message": str(e)}, user_id=current_user.id)
        return jsonify({'success': False, 'error': str(e), 'step': 'Unexpected error'}), 500

@app.route('/history', methods=['GET'])
@login_required
def history():
    videos = Video.query.filter_by(user_id=current_user.id).all()
    video_list = [{
        'filename': video.filename,
        'filepath': video.filepath,
        'prompt_text': video.prompt_text
    } for video in videos]
    return jsonify(video_list), 200

@app.route('/progress', methods=['GET'])
def progress():
    progress_info = get_progress(user_id="global")  # Change as needed
    return jsonify(progress_info), 200

# -------------------- Run the Server --------------------
if __name__ == '__main__':
    # For development only. In production, use a proper WSGI server like gunicorn or uWSGI.
    app.run(host="0.0.0.0", port=5000, debug=False)
