import os
import requests
import random
import subprocess
import asyncio
import json
import edge_tts

# --- [الإعدادات المستخرجة من Secrets] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
TWITCH_KEY = os.getenv("TWITCH_KEY")
# رابط تويتش المباشر
TWITCH_URL = f"rtmp://live.twitch.tv/app/{TWITCH_KEY}"

# روابط تطبيقاتك للترويج
MY_APPS = "Download our Apps: Luxury Estate Guide & ROI Assets on Play Store!"

STORY_TYPES = [
    "Cybersecurity Mysteries",
    "AI and Digital Consciousness",
    "Dark Web Unsolved Crimes"
]

async def fetch_story():
    """توليد القصة باستخدام AI"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write an immersive 500-word story about {random.choice(STORY_TYPES)}. "
        "At the end, add: 'Follow us for more AI stories and check our apps in the bio.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['cyber', 'hacker']}"
    )
    
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"--- [Error] AI Fetch: {e} ---")
        return None

async def broadcast():
    print("--- [System] Twitch AI Radio 24/7 Started ---")
    
    # تأكد أن الـ Key ليس فارغاً لتجنب خطأ Input/Output
    if not TWITCH_KEY or TWITCH_KEY == "None":
        print("--- [Critical Error] TWITCH_KEY is missing in Secrets! ---")
        return

    while True:
        data = await fetch_story()
        if not data: continue

        print(f"--- [Live] Story: {data.get('title', 'AI STORY')} ---")

        # 1. توليد الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. جلب فيديوهات الخلفية
        video_files = []
        for i, q in enumerate(data.get('queries', ['tech'])[:2]):
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1&orientation=landscape"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_url = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_url).content)
                video_files.append(fname)

        if not video_files: continue

        # 3. الفلتر السحري لتوحيد الأبعاد وتفادي الـ Mismatch
        # نقوم بتحويل كل فيديو لـ 426x240 مع إضافة حواف سوداء لو لزم الأمر
        v_prep = "".join([
            f"[{i}:v]scale=426:240:force_original_aspect_ratio=decrease,"
            f"pad=426:240:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];" 
            for i in range(len(video_files))
        ])
        v_concat = "".join([f"[v{i}]" for i in range(len(video_files))])
        
        final_filter = (
            f"{v_prep}{v_concat}concat=n={len(video_files)}:v=1:a=0[vraw];"
            f"[vraw]drawtext=text='FOLLOW FOR AI STORIES':fontcolor=yellow:fontsize=18:x=(w-text_w)/2:y=15:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*45\,w+tw):y=h-25:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg المستقر
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-r", "21", "-b:v", "400k",
            "-c:a", "aac", "-b:a", "64k", "-f", "flv", TWITCH_URL
        ]

        subprocess.run(cmd)

        # 5. تنظيف وراحة
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(broadcast())
