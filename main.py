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
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# الترويج لتطبيقاتك (مثل Luxury Estate Guide)
MY_APPS = "Check our Apps on Play Store: Luxury Estate Guide & ROI Assets!"

STORY_TYPES = ["Cybersecurity Myths", "AI Digital Horror", "Internet Mysteries"]

async def fetch_story():
    """توليد قصة مع مراعاة حدود الاستهلاك في Groq"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write a mysterious 500-word story about {random.choice(STORY_TYPES)}. "
        "At the end, add: 'Subscribe for more AI stories and check our apps in the description.' "
        "Return ONLY JSON: {'title': '...', 'story': '...', 'queries': ['tech', 'cyber']}"
    )
    
    try:
        # استخدام llama-3.1-8b لتقليل التكلفة والسرعة
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=60)
        
        if r.status_code == 429: # في حال تخطي حدود الطلبات
            print("--- [Limit] Groq Limit. Waiting 2 mins... ---")
            await asyncio.sleep(120)
            return None
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [System] AI Radio 24/7 is starting in 240p ---")
    
    while True:
        data = await fetch_story()
        if not data: continue

        # 1. توليد الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. جلب فيديوهات الخلفية
        video_files = []
        for i, q in enumerate(data.get('queries', ['dark'])[:3]):
            p_url = f"https://api.pexels.com/videos/search?query={q}&per_page=1&orientation=landscape"
            res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
            if 'videos' in res and len(res['videos']) > 0:
                v_url = res['videos'][0]['video_files'][0]['link']
                fname = f"b{i}.mp4"
                with open(fname, "wb") as f: f.write(requests.get(v_url).content)
                video_files.append(fname)

        if not video_files: continue

        # 3. الفلتر لضبط جودة 240p وإضافة الترويج
        # الإعدادات: 426x240 (جودة 240p القياسية)
        v_filters = "".join([f"[{i}:v]scale=426:240:force_original_aspect_ratio=increase,crop=426:240,setsar=1[v{i}];" for i in range(len(video_files))])
        v_concat = "".join([f"[v{i}]" for i in range(len(video_files))])
        
        final_filter = (
            f"{v_filters}{v_concat}concat=n={len(video_files)}:v=1:a=0[vout];"
            f"[vout]drawtext=text='SUBSCRIBE':fontcolor=yellow:fontsize=18:x=(w-text_w)/2:y=15:box=1:boxcolor=black@0.6,"
            f"drawtext=text='{MY_APPS}':fontcolor=white:fontsize=16:x=w-mod(t*40\,w+tw):y=h-25:box=1:boxcolor=red@0.5[finalv]"
        )

        # 4. أمر FFmpeg الموفر للطاقة والبيانات
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-r", "21", # إطار 21 لتخفيف الضغط
            "-b:v", "400k", "-c:a", "aac", "-b:a", "64k", "-f", "flv", YOUTUBE_URL
        ]

        print(f"--- [Live] Streaming Story: {data.get('title')} ---")
        subprocess.run(cmd)

        # 5. تنظيف وراحة لتجنب حظر Groq
        for f in video_files + [voice_file]:
            if os.path.exists(f): os.remove(f)
        await asyncio.sleep(50) # راحة كافية بين القصص

if __name__ == "__main__":
    asyncio.run(broadcast())
