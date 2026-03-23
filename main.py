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
# استخدام الرابط الأساسي (GitHub Actions يدعم DNS يوتيوب بشكل ممتاز)
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# --- [قائمة المواضيع] ---
STORY_TYPES = [
    "Cybersecurity mysteries and famous hackers",
    "Deep web urban legends and myths",
    "The future of AI and digital consciousness",
    "Unsolved internet crimes and mysteries"
]

async def fetch_unique_story():
    """توليد قصة فريدة بصيغة JSON"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    selected_topic = random.choice(STORY_TYPES)
    prompt = (
        f"Write an immersive and long story about: {selected_topic}. "
        "The story should be at least 600 words. Return ONLY a JSON object with: "
        "'title': 'catchy mysterious title', "
        "'full_story': 'the full text of the story', "
        "'search_queries': ['scene 1 keywords', 'scene 2 keywords', 'scene 3 keywords', 'scene 4 keywords']"
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
        return None
    except Exception as e:
        print(f"--- [Error] AI: {e} ---")
        return None

async def process_story_stream(data):
    """تحويل القصة إلى فيديو وبثها مباشرة"""
    try:
        title_text = data.get('title', 'AI STORY').upper().replace("'", "").replace(":", "")
        print(f"--- [Stream] Starting Broadcast: {title_text} ---")
        
        # 1. توليد الصوت
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
            print("--- [Error] No videos found on Pexels ---")
            return

        # 3. بناء الفلاتر (استخدام r-string لتجنب أخطاء البايثون)
       # تبسيط الفلتر لأقصى درجة لتجنب أخطاء GitHub Runner
        filter_complex = (
            f"concat=n={len(video_files)}:v=1:a=0[v];"
            f"[v]scale=1280:720,setsar=1,"
            f"drawtext=text='STORY':fontcolor=white:fontsize=40:x=60:y=h-80:box=1:boxcolor=black@0.5[finalv]"
        )

        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-b:v", "2500k", "-c:a", "aac", "-b:a", "128k", 
            "-shortest", "-f", "flv", YOUTUBE_URL
        ]
        
        subprocess.run(cmd)

    except Exception as e:
        print(f"--- [Error] Stream Process: {e} ---")

async def main():
    print("--- [System] AI Story Radio 24/7 Started ---")
    while True:
        story_data = await fetch_unique_story()
        if story_data:
            await process_story_stream(story_data)
            # مسح الملفات لتوفير مساحة الـ Runner
            for f in ["story_voice.mp3", "bg_0.mp4", "bg_1.mp4", "bg_2.mp4", "bg_3.mp4"]:
                if os.path.exists(f): os.remove(f)
        else:
            print("--- [System] AI failed, retrying in 30s... ---")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
