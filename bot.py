import os
from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

# Apne Telegram Bot ka Token aur Admin Telegram User ID yahan dalein
BOT_TOKEN = "8945315445:AAEgiE2p9WeImRHIql4GVBEqiInxx1vWYkI"
ADMIN_CHAT_ID = "6598432032"

# Simple Database ki jagah dictionary (Production ke liye MongoDB ya SQLite use kar sakte hain)
COMMENTS_DB = {}

@app.route('/')
def index():
    story_title = request.args.get('title', 'All Story FM')
    image_url = request.args.get('img', '')
    audio_url = request.args.get('audio', '')
    thread_id = request.args.get('thread', 'default')

    html_template = """
    <!DOCTYPE html>
    <html lang="hi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comments - {{ title }}</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: Arial, sans-serif; background: #0f0f0f; color: #fff; margin: 0; padding: 15px; }
            .card { background: #1f1f1f; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 15px; align-items: center; }
            .card img { width: 80px; height: 100px; object-fit: cover; border-radius: 5px; }
            input, textarea { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; background: #2f2f2f; border: 1px solid #444; color: #fff; border-radius: 5px; }
            button { background: #ff4757; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold; }
            button:hover { background: #ff6b81; }
            .comment-box { background: #1a1a1a; padding: 10px; border-radius: 5px; margin-top: 10px; border-left: 3px solid #ff4757; }
        </style>
    </head>
    <body>
        <div class="card">
            {% if img %}
            <img src="{{ img }}" alt="Story Image">
            {% endif %}
            <div>
                <h3>{{ title }}</h3>
                {% if audio %}
                <a href="{{ audio }}" target="_blank" style="color: #1e90ff; text-decoration: none;">🎵 Listen Audio URL</a>
                {% endif %}
            </div>
        </div>

        <h3>Apna Comment Likhein:</h3>
        <form id="commentForm">
            <input type="hidden" id="thread_id" value="{{ thread }}">
            <input type="hidden" id="story_title" value="{{ title }}">
            <input type="hidden" id="image_url" value="{{ img }}">
            <textarea id="comment_text" rows="3" placeholder="Yahan apna comment likhein..." required></textarea>
            <button type="submit">Comment bhejein</button>
        </form>

        <div id="status" style="margin-top: 10px; color: #2ed573;"></div>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            document.getElementById('commentForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                const user = tg.initDataUnsafe?.user;
                const userId = user ? user.id : 'Anonymous';
                const userName = user ? (user.first_name + (user.last_name ? ' ' + user.last_name : '')) : 'Guest';

                const data = {
                    thread_id: document.getElementById('thread_id').value,
                    title: document.getElementById('story_title').value,
                    image: document.getElementById('image_url').value,
                    comment: document.getElementById('comment_text').value,
                    user_id: userId,
                    user_name: userName
                };

                const response = await fetch('/submit_comment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if(result.success) {
                    document.getElementById('status').innerText = "Comment safaltapurvak admin ke paas bhej diya gaya hai!";
                    document.getElementById('comment_text').value = '';
                } else {
                    document.getElementById('status').innerText = "Kuch garbar ho gayi, kripya dubara koshish karein.";
                    document.getElementById('status').style.color = "#ff4757";
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, title=story_title, img=image_url, audio=audio_url, thread=thread_id)

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.json
    thread_id = data.get('thread_id')
    title = data.get('title')
    image = data.get('image')
    comment = data.get('comment')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    # Admin ko Telegram par image aur comment bhejna
    caption = f"💬 **New Comment on Story:** {title}\n\n👤 **User:** {user_name} (<code>{user_id}</code>)\n📝 **Comment:** {comment}\n\n👉 *Reply karne ke liye is message par Reply karein.*"
    
    if image:
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "photo": image,
            "caption": caption,
            "parse_mode": "HTML"
        }
    else:
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": caption,
            "parse_mode": "HTML"
        }

    response = requests.post(telegram_url, json=payload)
    
    # Save mapping for admin replies (optional database handling)
    if response.status_code == 200:
        res_data = response.json()
        msg_id = res_data['result']['message_id']
        COMMENTS_DB[msg_id] = user_id
        return jsonify({"success": True})
    
    return jsonify({"success": False})

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    if "message" in data and "reply_to_message" in data:
        message = data["message"]
        admin_id = str(message["from"]["id"])
        
        if admin_id == ADMIN_CHAT_ID:
            replied_msg_id = message["reply_to_message"]["message_id"]
            reply_text = message.get("text", "")
            
            # Check if we have the user ID for this message
            target_user_id = COMMENTS_DB.get(replied_msg_id)
            if target_user_id:
                # Send reply back to user
                send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": target_user_id,
                    "text": f"📩 **Admin ka reply aapke comment par:**\n\n{reply_text}",
                    "parse_mode": "HTML"
                }
                requests.post(send_url, json=payload)
                
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
