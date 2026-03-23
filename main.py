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

# روابط تطبيقاتك للترويج (عدلها بروابطك الحقيقية)
MY_APPS = "Check our apps on Play Store: Luxury Estate Guide & more!" 

STORY_TYPES = ["Cybersecurity mysteries", "AI Horror", "Deep Web Secrets"]

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # تحديث البرومبت ليشمل الترويج في نهاية القصة صوتياً
    prompt = (
        f"Write a mysterious 500-word story about {random.choice(STORY_TYPES)}. "
        f"At the very end of the story, add a sentence: 'If you enjoyed this, subscribe and check out our apps in the description.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['tech', 'dark']}"
    )
    
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        
        if r.status_code == 429:
            await asyncio.sleep(120)
            return None
        return json.loads(r.json()['choices'][0]['message']['content'])
    except:
        return None

async def broadcast():
    print("--- [System] AI Marketing Stream Started ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        title = data.get('title', 'AI RADIO').upper().replace("'", "")
        
        # 1. الصوت (يشمل جملة الترويج الآن)
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save("v.mp3")

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

        # 3. الفلتر المطور (نصوص الترويج والاشتراك)
        # توحيد المقاسات
        filter_parts = "".join([f"[{i}:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1[v{i}];" for i in range(len(video_files))])
        concat_in = "".join([f"[v{i}]" for i in range(len(video_files))])
        
        # إضافة نصوص ثابتة ومتحركة للترويج
        final_filter = (
            f"{filter_parts}{concat_in}concat=n={len(video_files)}:v=1:a=0[vout];"
            f"[vout]drawtext=text='SUBSCRIBE & HIT THE BELL':fontcolor=yellow:fontsize=30:x=(w-text_w)/2:y=40:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=25:x=w-mod(t*100\,w+tw):y=h-50:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg للبث
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", "v.mp3",
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "2500k",
            "-c:a", "aac", "-b:a", "128k", "-f", "flv", YOUTUBE_URL
        ]

        subprocess.run(cmd)

        # تنظيف وراحة لتوفير Groq
        for f in video_files + ["v.mp3"]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(broadcast())
