import os
import requests
import random
import subprocess
import asyncio
import json
import edge_tts

# --- [الإعدادات من الـ Secrets] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
TWITCH_KEY = os.getenv("TWITCH_KEY")
# رابط سيرفر تويتش (الأفضل للشرق الأوسط أو السيرفرات العالمية)
TWITCH_URL = f"rtmp://live.twitch.tv/app/{TWITCH_KEY}"

# الترويج لتطبيقاتك في الشات أو على الشاشة
MY_APPS = "Check my Apps: Luxury Estate Guide on Play Store!"

STORY_TYPES = ["Cybersecurity Horror", "AI Glitch Mysteries", "Dark Web Files"]

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write a mysterious 500-word story about {random.choice(STORY_TYPES)}. "
        "At the end, say: 'Follow for more stories and check our apps in the bio.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['matrix', 'hacker']}"
    )
    
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", # الموديل الأسرع
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        
        if r.status_code == 429:
            await asyncio.sleep(100)
            return None
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [Twitch] Starting 24/7 AI Stream in 240p ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        # 1. الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. الفيديوهات (توفير الموارد)
        video_files = []
        for i, q in enumerate(data.get('queries', ['tech'])[:2]): # فيديوهين بس لتخفيف الضغط
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1&orientation=landscape"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_link = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_link).content)
                video_files.append(fname)

        if not video_files: continue

        # 3. الفلتر (جودة 240p + ترويج لتطبيقاتك)
        filter_complex = (
            f"concat=n={len(video_files)}:v=1:a=0[v];"
            f"[v]scale=426:240:force_original_aspect_ratio=increase,crop=426:240,setsar=1,"
            f"drawtext=text='FOLLOW FOR MORE AI STORIES':fontcolor=yellow:fontsize=18:x=(w-text_w)/2:y=15:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*45\,w+tw):y=h-25:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg الموجه لتويتش
        # استخدام -re لضبط السرعة ومنع قفل البث
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-r", "21", # إطار 21 لتوفير الموارد
            "-b:v", "400k", "-c:a", "aac", "-b:a", "64k", "-f", "flv", TWITCH_URL
        ]

        print(f"--- [Live on Twitch] Story: {data.get('title')} ---")
        subprocess.run(cmd)

        # 5. تنظيف وراحة (لحماية Groq API)
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(broadcast())
