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
TWITCH_URL = f"rtmp://live.twitch.tv/app/{TWITCH_KEY}"

# الترويج لتطبيقاتك (مثل Luxury Estate Guide)
MY_APPS = "Check our Apps: Luxury Estate Guide on Play Store!"

STORY_TYPES = ["Cybersecurity Mysteries", "AI Horror Stories", "Deep Web Secrets"]

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write an immersive 500-word story about {random.choice(STORY_TYPES)}. "
        "At the end, say: 'Follow for more AI stories and check our apps in the bio.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['cyber', 'tech']}"
    )
    
    try:
        # استخدام الموديل الأسرع لتوفير الكوتا
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [Twitch] AI Story Radio 24/7 is starting ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        # 1. الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. الفيديوهات (نستخدم فيديوهات خفيفة)
        video_files = []
        for i, q in enumerate(data.get('queries', ['dark'])[:2]):
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1&orientation=landscape"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_url = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_url).content)
                video_files.append(fname)

        if not video_files: continue

        # 3. الفلتر لضبط 240p والترويج
        filter_complex = (
            f"concat=n={len(video_files)}:v=1:a=0[v];"
            f"[v]scale=426:240:force_original_aspect_ratio=increase,crop=426:240,setsar=1,"
            f"drawtext=text='FOLLOW FOR AI STORIES':fontcolor=yellow:fontsize=18:x=(w-text_w)/2:y=15:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*40\,w+tw):y=h-25:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg المستقر لتويتش
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-r", "21", 
            "-b:v", "400k", "-c:a", "aac", "-b:a", "64k", "-f", "flv", TWITCH_URL
        ]

        subprocess.run(cmd)

        # 5. تنظيف وراحة
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(50)

if __name__ == "__main__":
    asyncio.run(broadcast())
