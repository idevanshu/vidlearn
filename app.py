import os
import json
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Video
from main import generate_video
from quiz import generate_quiz
from progress import progress_data
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to your own secret key!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Database stored locally as site.db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the application
db.init_app(app)

migrate = Migrate(app, db)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

CORS(app)

# Set up Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users to login

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# -------------------- Frontend Routes --------------------

# Home page
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# -------------------- Authentication Routes --------------------

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful, please log in.")
        return redirect(url_for('login'))
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to home page.
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully.")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.")
            return redirect(url_for('login'))
    return render_template('login.html')

# Logout: after logout redirect to login page
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for('login'))

# -------------------- Video Generation & Quiz Routes --------------------

# Define a global output folder and create it if it doesn't exist.
OUTPUT_FOLDER = os.path.join(os.getcwd(), "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Video Generation
@app.route('/generate-video', methods=['POST'])
@login_required
def generate_video_endpoint():
    try:
        # Expect form-data (multipart request)
        prompt = request.form.get('prompt')
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required.',
                'step': 'Initial validation'
            }), 400

        # Handle file attachment if provided
        attachment = request.files.get('attachment')
        attachment_filename = None
        if attachment:
            filename = secure_filename(attachment.filename)
            # Determine the correct subfolder (you can customize these folders further)
            attachment_folder = os.path.join(app.config['UPLOAD_FOLDER'], "pdf") \
                                if filename.lower().endswith('.pdf') else \
                                os.path.join(app.config['UPLOAD_FOLDER'], "images")
            os.makedirs(attachment_folder, exist_ok=True)
            filepath = os.path.join(attachment_folder, filename)
            attachment.save(filepath)
            attachment_filename = filename
            # Optionally, augment the prompt with attachment info
            prompt += f" (See attached file: {filename})"

        # Create a user-specific output folder inside the global OUTPUT_FOLDER.
        user_output_folder = os.path.join(OUTPUT_FOLDER, f"{current_user.username}_output")
        os.makedirs(user_output_folder, exist_ok=True)

        # Compute a sanitized filename based on the user and prompt.
        words = prompt.split()
        filename_base = "_".join(words[:10])
        raw_filename = f"{current_user.id}_{filename_base}.mp4"
        computed_filename = secure_filename(raw_filename)  # Sanitizes the filename
        # Build the full file path inside the user output folder.
        output_file_path = os.path.join(user_output_folder, computed_filename)

        app.logger.info("Starting video generation for prompt: %s", prompt)
        # Pass the full output file path to your video generation function.
        success = generate_video(prompt, output_file_path)

        if success and os.path.exists(output_file_path):
            app.logger.info("Video generated successfully. File: %s", output_file_path)
            try:
                with open("scripts.json", "r", encoding="utf-8") as f:
                    script = json.load(f)
            except Exception as e:
                app.logger.error("Error reading scripts.json: %s", str(e))
                return jsonify({
                    'success': False,
                    'error': 'Error reading generated script file.',
                    'step': 'Script reading'
                }), 500

            # Save the generated video record in the database.
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
            })
        else:
            app.logger.error("Video generation failed or output file not found.")
            return jsonify({
                'success': False,
                'error': 'Video generation failed.',
                'step': 'Video generation'
            }), 500

    except Exception as e:
        app.logger.exception("Exception during video generation:")
        return jsonify({
            'success': False,
            'error': str(e),
            'step': 'Unexpected error'
        }), 500

@app.route('/download-video', methods=['GET'])
@login_required
def download_video():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename query parameter is required.'}), 400
    user_output_folder = os.path.join(OUTPUT_FOLDER, f"{current_user.username}_output")
    output_path = os.path.join(user_output_folder, filename)
    app.logger.info("Download request: output_path = %s", output_path)
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)
    else:
        app.logger.error("File not found at: %s", output_path)
        return jsonify({'error': 'File not found.'}), 404

# Generate Quiz based on video script
@app.route('/generate-quiz', methods=['POST'])
@login_required
def generate_quiz_endpoint():
    try:
        data = request.get_json()
        script = data.get('script')
        if not script:
            return jsonify({
                'success': False,
                'error': 'Script is required to generate quiz.',
                'step': 'Initial validation'
            }), 400

        app.logger.info("Starting quiz generation based on the script.")
        quiz = generate_quiz(script)
        if quiz:
            app.logger.info("Quiz generation successful.")
            return jsonify({
                'success': True,
                'quiz': quiz,
                'step': 'Completed'
            })
        else:
            app.logger.error("Quiz generation failed.")
            return jsonify({
                'success': False,
                'error': 'Quiz generation failed.',
                'step': 'Quiz generation'
            }), 500

    except Exception as e:
        app.logger.exception("Exception during quiz generation:")
        return jsonify({
            'success': False,
            'error': str(e),
            'step': 'Unexpected error'
        }), 500

# History: Return generated videos for the current user
@app.route('/history', methods=['GET'])
@login_required
def history():
    videos = Video.query.filter_by(user_id=current_user.id).all()
    video_list = [{
        'filename': video.filename,
        'filepath': video.filepath,
        'prompt_text': video.prompt_text
    } for video in videos]
    return jsonify(video_list)

# Progress endpoint (for polling from the front end)
@app.route('/progress', methods=['GET'])
def get_progress():
    # In a real system, update progress_data during video generation.
    return jsonify(progress_data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
