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

# --- [قائمة المواضيع] ---
STORY_TYPES = [
    "Cybersecurity mysteries and dark web legends",
    "The future of AI and digital consciousness",
    "Space anomalies and extraterrestrial technology",
    "Unsolved internet crimes and deep web secrets"
]

async def fetch_unique_story():
    """توليد قصة فريدة بصيغة JSON باستخدام Groq"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    selected_topic = random.choice(STORY_TYPES)
    prompt = (
        f"Write an immersive story about: {selected_topic}. "
        "The story should be around 500 words. Return ONLY a JSON object with: "
        "'title': 'short title', 'full_story': 'text', "
        "'queries': ['keyword1', 'keyword2', 'keyword3']"
    )
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.8
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        return json.loads(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"--- [Error] AI: {e} ---")
        return None

async def process_story_stream(data):
    """تحويل القصة لفيديو وبثها مع توحيد المقاسات"""
    try:
        title_text = data.get('title', 'AI STORY').upper().replace("'", "").replace(":", "")
        print(f"--- [Stream] Preparing: {title_text} ---")
        
        # 1. توليد الصوت
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['full_story'], "en-US-ChristopherNeural").save(voice_file)

        # 2. جلب فيديوهات الخلفية
        video_files = []
        p_headers = {"Authorization": PEXELS_KEY}
        for i, query in enumerate(data['queries'][:3]):
            p_url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=landscape"
            r = requests.get(p_url, headers=p_headers).json()
            if 'videos' in r and len(r['videos']) > 0:
                v_link = r['videos'][0]['video_files'][0]['link']
                fname = f"bg_{i}.mp4"
                with open(fname, "wb") as f:
                    f.write(requests.get(v_link).content)
                video_files.append(fname)

        if not video_files: return

        # 3. بناء الفلاتر لتوحيد المقاسات (حل مشكلة SAR و Match Parameters)
        #
        filter_parts = ""
        for i in range(len(video_files)):
            filter_parts += f"[{i}:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1[v{i}];"
        
        concat_inputs = "".join([f"[v{i}]" for i in range(len(video_files))])
        final_filter = (
            f"{filter_parts}"
            f"{concat_inputs}concat=n={len(video_files)}:v=1:a=0[vout];"
            f"[vout]drawtext=text='{title_text}':fontcolor=white:fontsize=45:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.6[finalv]"
        )

        # 4. أمر FFmpeg النهائي للبث
        cmd = [
            "ffmpeg", "-re", "-y",
            *sum([["-i", f] for f in video_files], []),
            "-i", voice_file,
            "-filter_complex", final_filter,
            "-map", "[finalv]", "-map", f"{len(video_files)}:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "2500k",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-f", "flv", YOUTUBE_URL
        ]
        
        print("--- [System] Pushing Stream to YouTube ---")
        subprocess.run(cmd)

    except Exception as e:
        print(f"--- [Error] Process: {e} ---")

async def main():
    while True:
        story_data = await fetch_unique_story()
        if story_data:
            await process_story_stream(story_data)
            # تنظيف الملفات
            for f in ["v.mp3", "bg_0.mp4", "bg_1.mp4", "bg_2.mp4"]:
                if os.path.exists(f): os.remove(f)
        else:
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
