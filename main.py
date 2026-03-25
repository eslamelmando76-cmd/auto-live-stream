import os
import requests
import subprocess
import asyncio
import json
import edge_tts
import random

# --- [الإعدادات الجاهزة لليوتيوب] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY") 
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
MY_APPS = "Download our Apps: Luxury Estate Guide on Play Store!"

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = "Write a 300-word mystery story. Return JSON: {'title': '...', 'story': '...', 'queries': ['cyberpunk', 'city', 'night']}"
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=30)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def download_video(queries):
    query = random.choice(queries) if queries else "technology"
    p_url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=landscape"
    res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
    if 'videos' in res and len(res['videos']) > 0:
        video = random.choice(res['videos'])
        v_link = video['video_files'][0]['link']
        video_file = "b0.mp4"
        with open(video_file, "wb") as f:
            f.write(requests.get(v_link).content)
        return video_file
    return None

async def broadcast():
    print("--- [System] YouTube Live 24/7 is Starting ---")
    if not STREAM_KEY:
        print("--- [Error] STREAM_KEY is missing! ---")
        return

    while True:
        data = await fetch_story()
        if not data: 
            await asyncio.sleep(10)
            continue

        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        queries = data.get('queries', [])
        video_file = await download_video(queries)
        
        if not video_file: continue

        # الفلتر الجديد: خلفية ضبابية + فيديو في النص + تنبيه الاشتراك
        filter_complex = (
            "[0:v]scale=426:240,boxblur=20:10[bg];"
            "[0:v]scale=320:180[mainv];"
            "[bg][mainv]overlay=(W-w)/2:(H-h)/2-10[vid];"
            f"[vid]drawtext=text='🔔 PLEASE SUBSCRIBE FOR MORE STORIES':fontcolor=lime:fontsize=15:x=(w-tw)/2:y=h-60:enable='lt(mod(t\,30)\,5)',"
            f"drawtext=text='Story\: {data['title']}':fontcolor=yellow:fontsize=14:x=(w-tw)/2:y=15:box=1:boxcolor=black@0.7,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*45\,w+tw):y=h-30:box=1:boxcolor=red@0.6[finalv]"
        )

        # السطر اللي كان فيه المشكلة (تأكد إنه واخد نفس مسافة اللي فوقه)
        cmd = [
            "ffmpeg", "-re", "-y", "-i", video_file, "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", 
            "-r", "20", "-g", "40", "-b:v", "400k",
            "-c:a", "aac", "-b:a", "64k", "-ar", "44100",
            "-f", "flv", YOUTUBE_URL
        ]

        subprocess.run(cmd)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(broadcast())
