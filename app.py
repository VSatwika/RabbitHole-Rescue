import os
import re
import requests
from flask import Flask, request, redirect, url_for, session, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
    api_base_url="https://www.googleapis.com/oauth2/v3/",
    userinfo_endpoint="https://www.googleapis.com/oauth2/v3/userinfo",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs"
)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    channel_id = db.Column(db.String(100), unique=True)
    channel_name = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/login")
def login():
    return google.authorize_redirect(url_for("authorized", _external=True))

@app.route("/login/callback")
def authorized():
    token = google.authorize_access_token()
    if not token:
        return "Access Denied"

    user_info = google.get("userinfo").json()
    google_id = user_info.get("id") or user_info.get("sub")  # Fix KeyError

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User(google_id=google_id, name=user_info["name"], email=user_info["email"])
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_channels = Channel.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", user=current_user, channels=user_channels)

@app.route("/add_channel", methods=["POST"])
@login_required
def add_channel():
    profile_url = request.form.get("profile_url")
    channel_id = extract_channel_id(profile_url)

    if not channel_id:
        return "Invalid Channel URL", 400

    # Fetch channel details
    channel_name = get_channel_name(channel_id)
    if not channel_name:
        return "Failed to fetch channel details", 400

    # Save channel to DB
    new_channel = Channel(user_id=current_user.id, channel_id=channel_id, channel_name=channel_name)
    db.session.add(new_channel)
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/channel/<channel_id>")
@login_required
def view_channel(channel_id):
    categorized_videos = get_channel_videos(channel_id)
    return render_template("videos.html", categorized_videos=categorized_videos)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("home"))

# ---------------- YouTube API Helper Functions ----------------

def extract_channel_id(profile_url):
    """Extracts the channel ID from a YouTube handle (@username) or full URL."""
    # Extract handle (@username)
    match = re.search(r"@([a-zA-Z0-9_-]+)", profile_url)
    if match:
        username = match.group(1)
        return get_channel_id_from_handle(username)

    # Extract from full YouTube URL
    match = re.search(r"channel/([a-zA-Z0-9_-]+)", profile_url)
    if match:
        return match.group(1)

    return None  # If invalid format

def get_channel_id_from_handle(handle):
    """Fetches the channel ID from a YouTube handle (@username)."""
    url = f"{YOUTUBE_API_URL}channels?part=id&forHandle={handle}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    
    if "items" in response and len(response["items"]) > 0:
        return response["items"][0]["id"]
    
    return None


def get_channel_id_from_username(username):
    """Fetches the channel ID from a YouTube username."""
    url = f"{YOUTUBE_API_URL}channels?part=id&forUsername={username}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    if "items" in response and len(response["items"]) > 0:
        return response["items"][0]["id"]
    return None

def get_channel_name(channel_id):
    """Fetches the channel name using YouTube API."""
    url = f"{YOUTUBE_API_URL}channels?part=snippet&id={channel_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    if "items" in response and len(response["items"]) > 0:
        return response["items"][0]["snippet"]["title"]
    return None

def get_channel_videos(channel_id):
    """Fetches recent videos from a YouTube channel and categorizes them with tags using AI."""
    url = f"{YOUTUBE_API_URL}search?part=snippet&channelId={channel_id}&maxResults=10&order=date&type=video&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    
    categorized_videos = {}

    if "items" in response:
        for item in response["items"]:
            title = item["snippet"]["title"]
            description = item["snippet"].get("description", "")
            
            category, tags = categorize_video(title, description)  # Now returns tags too
            
            video = {
                "title": title,
                "video_id": item["id"]["videoId"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                "tags": tags  # Add tags to video data
            }
            
            if category not in categorized_videos:
                categorized_videos[category] = []
            categorized_videos[category].append(video)
    
    return categorized_videos


@app.route('/get_videos/<channel_id>')
def get_videos(channel_id):
    """Fetch latest videos from a YouTube channel."""
    url = f"{YOUTUBE_API_URL}search?part=snippet&channelId={channel_id}&order=date&maxResults=10&type=video&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    
    videos = []
    if "items" in response:
        for item in response["items"]:
            videos.append({
                "title": item["snippet"]["title"],
                "videoId": item["id"]["videoId"],
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"]
            })
    
    return jsonify(videos)


@app.route('/delete_creator', methods=['POST'])
@login_required
def delete_creator():
    """Deletes a saved creator from the database for the logged-in user."""
    data = request.json
    channel_id = data.get('channel_id')

    channel = Channel.query.filter_by(user_id=current_user.id, channel_id=channel_id).first()
    
    if channel:
        db.session.delete(channel)
        db.session.commit()
        return jsonify({"success": True, "message": "Creator removed successfully"})
    
    return jsonify({"error": "Creator not found"}), 404


def categorize_video(title, description):
    """Uses Groq's AI to categorize a video and generate relevant tags."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": 
                "You are an AI that categorizes YouTube videos into a single-word topic "
                "and generates exactly 5 relevant comma-separated tags. "
                "Respond ONLY in this format:\n"
                "Category: [Category Name]\nTags: tag1, tag2, tag3, tag4, tag5"},
            {"role": "user", "content": f"Title: {title}\nDescription: {description}\nCategory & Tags:"}
        ]
    }
    
    response = requests.post(GROQ_API_URL, json=payload, headers=headers).json()
    
    # Debugging: Print AI response
    print("Groq API Response:", response)
    
    category, tags = "Unknown", []

    if "choices" in response and response["choices"]:
        raw_response = response["choices"][0]["message"]["content"].strip()

        # Extract category using regex
        category_match = re.search(r"Category:\s*(.+)", raw_response)
        if category_match:
            category = category_match.group(1).strip()

        # Extract tags using regex
        tags_match = re.search(r"Tags:\s*(.+)", raw_response)
        if tags_match:
            tags = [tag.strip() for tag in tags_match.group(1).split(",")]

    return category, tags





if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)