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
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# روابط تطبيقاتك للترويج
MY_APPS = "Download our Apps: Luxury Estate Guide & ROI Assets on Play Store!"

STORY_TYPES = ["Cybersecurity mysteries", "AI future horror", "Dark web urban legends"]

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write a mysterious 500-word story about {random.choice(STORY_TYPES)}. "
        f"At the end, add this exact sentence: 'Thanks for watching. Subscribe, hit the bell, and check our amazing apps in the description.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['cyber', 'dark', 'tech']}"
    )
    
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", # الموديل الأسرع لتوفير الوقت
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        
        if r.status_code == 429:
            print("--- [Limit] Groq Rate Limit. Waiting... ---")
            await asyncio.sleep(120)
            return None
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [System] AI Story Radio 24/7 is Live ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        title = data.get('title', 'AI STORY').upper().replace("'", "")
        print(f"--- [Stream] Broadcasting: {title} ---")

        # 1. الصوت (يشمل الترويج الآن)
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. جلب فيديوهات الخلفية
        video_files = []
        for i, q in enumerate(data.get('queries', ['tech'])[:3]):
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1&orientation=landscape"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_url = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_url).content)
                video_files.append(fname)

        if not video_files: continue

        # 3. الفلتر العبقري (توحيد مقاسات لـ 240p + نصوص ترويجية)
        # توحيد المقاسات لـ 240p (426x240)
        filter_complex = (
            f"concat=n={len(video_files)}:v=1:a=0[v];"
            f"[v]scale=426:240:force_original_aspect_ratio=increase,crop=426:240,setsar=1,"
            f"drawtext=text='SUBSCRIBE':fontcolor=yellow:fontsize=20:x=(w-text_w)/2:y=20:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=18:x=w-mod(t*50\,w+tw):y=h-30:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg للبث المباشر
        # استخدام -re لتثبيت السرعة
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "800k",
            "-c:a", "aac", "-b:a", "96k", "-f", "flv", YOUTUBE_URL
        ]

        subprocess.run(cmd)

        # 5. تنظيف وراحة
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(broadcast())
