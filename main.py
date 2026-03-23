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
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

STORY_TYPES = [
    "Dark web cyber horror stories",
    "Unsolved digital mysteries",
    "Future AI world domination secrets",
    "Famous cybersecurity breaches"
]

async def fetch_story():
    """توليد قصة جديدة من AI"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Write a mysterious 500-word story about {random.choice(STORY_TYPES)}. Return JSON: {{'title': '...', 'full_story': '...', 'queries': ['nature', 'tech', 'dark']}}"
    
    try:
        r = requests.post(url, headers=headers, json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=60)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"Error AI: {e}")
        return None

async def run_broadcast():
    """الدورة اللانهائية للبث"""
    print("--- [System] Starting 24/7 Live Stream ---")
    
    while True: # حلقة لا نهائية لضمان عدم توقف البث
        data = await fetch_story()
        if not data:
            await asyncio.sleep(10)
            continue
            
        # 1. الصوت
        await edge_tts.Communicate(data['full_story'], "en-US-ChristopherNeural").save("v.mp3")
        
        # 2. جلب الفيديوهات
        video_inputs = []
        for i, q in enumerate(data['queries'][:3]):
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_link = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_link).content)
                video_inputs.append(fname)

        if not video_inputs: continue

        # 3. توحيد المقاسات والدمج (حل مشكلة SAR)
        filter_parts = "".join([f"[{i}:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1[v{i}];" for i in range(len(video_inputs))])
        concat_part = "".join([f"[v{i}]" for i in range(len(video_inputs))])
        final_filter = f"{filter_parts}{concat_part}concat=n={len(video_inputs)}:v=1:a=0[vout];[vout]drawtext=text='LIVE AI RADIO':fontcolor=white:fontsize=50:x=50:y=50:box=1:boxcolor=black@0.5[finalv]"

        # 4. الأمر المطور (بدون -shortest لضمان الانتقال السلس)
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_inputs], []),
            "-i", "v.mp3",
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_inputs)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "2500k",
            "-c:a", "aac", "-b:a", "128k", "-f", "flv", YOUTUBE_URL
        ]
        
        print(f"--- [Live] Broadcasting: {data['title']} ---")
        subprocess.run(cmd) # هيفضل شغال لحد ما القصة تخلص ويرجع يعيد من الأول

        # تنظيف الملفات فوراً
        for f in video_inputs + ["v.mp3"]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    asyncio.run(run_broadcast())
