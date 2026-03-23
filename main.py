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
# يفضل استخدام الرابط الأساسي، GitHub DNS قوي جداً وسيتمكن من الوصول إليه
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# --- [قائمة أنواع القصص المتجددة] ---
STORY_TYPES = [
    "Mysterious cybersecurity breaches and famous hacks",
    "The hidden history of dark web mysteries",
    "Artificial Intelligence evolution and the future of humanity",
    "True unsolved digital crimes and internet legends",
    "Deep space signals and the search for extraterrestrial tech",
    "The secret history of Silicon Valley secrets"
]

async def fetch_unique_story():
    """توليد قصة فريدة باستخدام الموديل المستقر llama-3.1-8b-instant"""
    selected_topic = random.choice(STORY_TYPES)
    print(f"--- [AI] Topic: {selected_topic} ---")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Write an immersive story about: {selected_topic}. "
        "The story should be around 600 words. Return ONLY a JSON object with: "
        "'title': 'short title', 'full_story': 'text', "
        "'search_queries': ['keywords1', 'keywords2', 'keywords3', 'keywords4']"
    )
    
    payload = {
        "model": "llama-3.1-8b-instant", # الموديل المختار بناءً على حدود الاستهلاك
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.85
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return json.loads(response.json()['choices'][0]['message']['content'])
        print(f"--- [Error] AI Status: {response.status_code} ---")
        return None
    except Exception as e:
        print(f"--- [Error] AI Generation: {e} ---")
        return None

async def process_story_stream(data):
    """تحويل القصة إلى فيديو وبثها مباشرة مع معالجة FFmpeg المتقدمة"""
    try:
        title_text = data.get('title', 'AI STORY').upper().replace("'", "").replace(":", "")
        print(f"--- [Stream] Starting: {title_text} ---")
        
        # 1. تحويل النص لصوت
        voice_file = "story_voice.mp3"
        communicate = edge_tts.Communicate(data['full_story'], "en-US-ChristopherNeural")
        await communicate.save(voice_file)

        # 2. جلب فيديوهات الخلفية من Pexels
        video_files = []
        p_headers = {"Authorization": PEXELS_KEY}
        for i, query in enumerate(data['search_queries'][:4]):
            p_url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=landscape"
            r = requests.get(p_url, headers=p_headers).json()
            if 'videos' in r and len(r['videos']) > 0:
                v_link = r['videos'][0]['video_files'][0]['link']
                filename = f"bg_{i}.mp4"
                with open(filename, "wb") as f:
                    f.write(requests.get(v_link).content)
                video_files.append(filename)

        if not video_files:
            print("--- [Error] No videos found! ---")
            return

        # 3. بناء فلاتر FFmpeg (نظام القائمة لضمان الاستقرار)
# استخدام r قبل النص (Raw String) لمنع خطأ الـ Escape Sequence في بايثون
        filter_complex = (
            f"concat=n={len(video_files)}:v=1:a=0[v];"
            f"[v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,"
            r"drawtext=text='STORY\: " + title_text + r"':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.6,"
            r"drawtext=text='%{localtime\:%H\\:%M\\:%S}':fontcolor=yellow:fontsize=24:x=w-text_w-20:y=20:box=1:boxcolor=black@0.4[finalv]"
        )

        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", 2500000,
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-f", "flv", YOUTUBE_URL
        ]
        
        # تشغيل البث ومراقبة المخرجات
        process = subprocess.run(cmd)
        if process.returncode != 0:
            print(f"--- [Error] FFmpeg exited with code {process.returncode} ---")

    except Exception as e:
        print(f"--- [Error] Processing: {e} ---")

async def main():
    print("--- [System] AI Story Radio 24/7 Started on GitHub ---")
    while True:
        story_data = await fetch_unique_story()
        if story_data:
            await process_story_stream(story_data)
            # تنظيف الملفات فوراً لتوفير مساحة الـ Runner
            for f in ["story_voice.mp3", "bg_0.mp4", "bg_1.mp4", "bg_2.mp4", "bg_3.mp4"]:
                if os.path.exists(f): os.remove(f)
        else:
            print("--- [System] AI failed, sleeping 30s... ---")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
