# RabbitHole-Rescue

# 🐇 RabbitHole Rescue

> A YouTube distraction filter built to help you **watch what you came for** – and escape the endless scroll.

## 🎯 The Idea

We’ve all been there:  
You come to YouTube for one productive video — and hours later, you’re watching “How to Talk to a Giraffe.”  
This project was inspired by *that exact meme moment* — and it’s my small attempt to rescue us from those rabbit holes.

## ✨ What It Does

- Lets users **add their favorite YouTube channels**
- Uses **AI to categorize videos** by topic
- Organizes content into clean, focused **categories with tags**
- Simple login using **Google OAuth**
- Users can **delete channels** anytime
- Clean distraction-free layout to **actually watch what you came for**

## 🛠️ Built With

- **Flask** – Python backend framework
- **SQLAlchemy** – Database ORM
- **Google OAuth** – For authentication
- **YouTube Data API v3** – To fetch channel & video data
- **Groq API (LLaMA3)** – For video content categorization & tagging

## 📦 Setup Instructions

# 1. Clone this repo
git clone https://github.com/your-username/rabbithole-rescue.git
cd rabbithole-rescue
# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate
# 3. Install dependencies
pip install -r requirements.txt
# 4. Set up environment variables
# Create a .env file in the root directory and add the following:
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
YOUTUBE_API_KEY=your_youtube_api_key
GROQ_API_KEY=your_groq_api_key
# 5. Run the app
flask run


