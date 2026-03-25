import os
import requests
import random
import subprocess
import asyncio
import json
import edge_tts

# --- [الإعدادات] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
TWITCH_KEY = os.getenv("TWITCH_KEY")

# السطر الجديد ليوتيوب
YOUTUBE_KEY = os.getenv("TWITCH_KEY") # استخدم نفس السكرت القديم عشان متبدأش من الأول
TWITCH_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_KEY}"

MY_APPS = "Download our Apps: Luxury Estate Guide on Play Store!"

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = "Write a 400-word mystery story. Return JSON: {'title': '...', 'story': '...', 'queries': ['dark']}"
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [System] Twitch Live Starting ---")
    if not TWITCH_KEY or TWITCH_KEY == "None":
        print("--- [Error] TWITCH_KEY is missing! Check Secrets. ---")
        return

    while True:
        data = await fetch_story()
        if not data: continue

        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        video_files = []
        p_url = f"https://api.pexels.com/videos/search?query=tech&per_page=1&orientation=landscape"
        res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
        if 'videos' in res:
            v_url = res['videos'][0]['video_files'][0]['link']
            with open("b0.mp4", "wb") as f: f.write(requests.get(v_url).content)
            video_files.append("b0.mp4")

        # فلتر توحيد الأبعاد لـ 240p لمنع الـ Mismatch
        filter_complex = (
            "[0:v]scale=426:240:force_original_aspect_ratio=decrease,pad=426:240:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
            f"[v0]drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*40\,w+tw):y=h-25:box=1:boxcolor=red@0.5[finalv]"
        )

        # أمر FFmpeg المعدل لزيادة الاستقرار
        cmd = [
            "ffmpeg", "-re", "-y", "-i", "b0.mp4", "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-r", "21", "-b:v", "400k",
            "-c:a", "aac", "-b:a", "64k", "-f", "flv", 
            "-flvflags", "no_duration_filesize", # هام جداً لاستقرار البث
            TWITCH_URL
        ]

        subprocess.run(cmd)
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(broadcast())
