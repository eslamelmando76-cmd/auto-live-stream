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

# الترويج لتطبيقاتك
MY_APPS = "Download our Apps: Luxury Estate Guide & ROI Assets on Play Store!"

STORY_TYPES = ["Cybersecurity Mysteries", "AI Horror Stories", "Dark Web Legends"]

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        f"Write an immersive 500-word story about {random.choice(STORY_TYPES)}. "
        "End with: 'Subscribe and check our apps in the description.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['dark', 'tech']}"
    )
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except:
        return None

async def broadcast():
    print("--- [System] AI Radio 24/7 is Live ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        # 1. الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. الفيديوهات
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

        # 3. الفلتر (توحيد مقاسات + ترويج متحرك)
        # حل مشكلة SAR وتطابق الأبعاد
        v_filters = "".join([f"[{i}:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1[v{i}];" for i in range(len(video_files))])
        v_concat = "".join([f"[v{i}]" for i in range(len(video_files))])
        
        final_filter = (
            f"{v_filters}{v_concat}concat=n={len(video_files)}:v=1:a=0[vout];"
            f"[vout]drawtext=text='SUBSCRIBE & HIT THE BELL':fontcolor=yellow:fontsize=35:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.7,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=28:x=w-mod(t*100\,w+tw):y=h-60:box=1:boxcolor=red@0.6[finalv]"
        )

        # 4. أمر FFmpeg مع إضافة -re لمنع السرعة الزائدة
        cmd = [
            "ffmpeg", "-re", "-y", # -re هنا هو الحل لمشكلة السرعة
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "2500k",
            "-c:a", "aac", "-b:a", "128k", "-f", "flv", YOUTUBE_URL
        ]

        subprocess.run(cmd)

        # تنظيف وراحة
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(broadcast())
