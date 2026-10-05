import os
import sys
import time
import subprocess

# ==========================================
# 🔴 APNI DETAILS YAHAN DALEIN 🔴
# ==========================================
API_ID = 34801155                      # Apna API ID dalein (bina quotes ke)
API_HASH = "d7846c4d0f2c343dd5b67c80d45409e8"           # Apna API HASH dalein
BOT_TOKEN = "8808145635:AAE4KqnrT-7hDSoW7svkVvsfthj9NINN5x0"         # Apna Bot Token dalein
CHANNEL_ID = -1003545857457          # Apne Channel ka ID yahan dalein
# ==========================================


# --- AUTO SETUP (Koi jhanjhat nahi) ---
def auto_setup():
    print("🔄 System check kar raha hoon...")
    
    try:
        import pyrogram
        import tgcrypto
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("📦 Kuch libraries missing hain. Auto-install ho rahi hain...")
        os.system(f"{sys.executable} -m pip install pyrogram tgcrypto playwright")
        print("✅ Libraries install ho gayi! Ek baar phir se run karein.")
        sys.exit()

    if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")):
        print("🌐 Web Browser install ho raha hai (isme 1-2 minute lagenge)...")
        os.system(f"{sys.executable} -m playwright install chromium")
        os.system(f"{sys.executable} -m playwright install-deps")
        print("✅ Browser ready!")

    os.system("pulseaudio -D 2>/dev/null")
    
    if "DISPLAY" not in os.environ:
        print("🖥️ Virtual Screen auto-start ho rahi hai...")
        os.execlp("xvfb-run", "xvfb-run", "-a", sys.executable, *sys.argv)

auto_setup()


# --- MAIN BOT CODE ---
from pyrogram import Client, filters
from playwright.sync_api import sync_playwright

app = Client("pocketfm_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def record_and_upload(client, message, story_id, start_ep, end_ep):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./session_data",
            headless=False,
            args=["--start-maximized", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()

        for ep_num in range(start_ep, end_ep + 1):
            status_msg = message.reply_text(f"⏳ Story '{story_id}' ka Episode {ep_num} record ho raha hai...")
            audio_file = f"{story_id}_Ep_{ep_num}.mp3"
            
            episode_url = f"https://www.pocketfm.com/show/{story_id}/episode-{ep_num}"
            
            try:
                page.goto(episode_url)
                time.sleep(5)
                
                page.click("button.play-icon") 
                
                # 600 seconds (10 mins) recording time
                ffmpeg_cmd = f"ffmpeg -y -f pulse -i default -t 600 -c:a libmp3lame -q:a 2 {audio_file}"
                subprocess.run(ffmpeg_cmd, shell=True, check=True)
                
                status_msg.edit_text(f"✅ Episode {ep_num} record ho gaya. Channel par upload ho raha hai...")
                
                # Channel ID par upload hoga
                client.send_audio(
                    chat_id=CHANNEL_ID,
                    audio=audio_file,
                    caption=f"🎧 Story: {story_id} | Episode: {ep_num}"
                )
                
                status_msg.edit_text(f"🎉 Episode {ep_num} channel me successfully upload ho gaya!")
                
            except Exception as e:
                status_msg.edit_text(f"❌ Error aaya: {e}")
            
            finally:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    
        browser.close()
        message.reply_text("✅ Backup poora hua!")

@app.on_message(filters.command("backup") & filters.private)
def handle_backup(client, message):
    args = message.text.split()
    if len(args) != 4:
        message.reply_text("Sahi command use karein:\n`/backup [story_name] [start_ep] [end_ep]`\nExample: `/backup my-story 1 10`")
        return
    
    story_id = args[1]
    
    try:
        start_ep = int(args[2])
        end_ep = int(args[3])
    except ValueError:
        message.reply_text("Episodes ke liye valid number use karein.")
        return
        
    message.reply_text(f"🚀 '{story_id}' ke episodes {start_ep} se {end_ep} tak process shuru...")
    record_and_upload(client, message, story_id, start_ep, end_ep)

print("🤖 Bot is running... Telegram me jakar command dein!")
app.run()
        
