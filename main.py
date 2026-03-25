import os
import requests
import subprocess
import asyncio
import json
import edge_tts

# --- [الإعدادات الجاهزة لليوتيوب] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
# بنسحب المفتاح من الصندوق اللي سميناه STREAM_KEY في جيت هاب
STREAM_KEY = os.getenv("STREAM_KEY") 

# رابط سيرفر يوتيوب الرئيسي - ده أسرع ومستقر جداً
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

MY_APPS = "Check out our Apps: Luxury Estate Guide on Play Store!"

async def fetch_story():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = "Write a 300-word interesting tech mystery story. Return JSON: {'title': '...', 'story': '...', 'queries': ['cyber']}"
    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.1-8b-instant", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=30)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return None

async def broadcast():
    print("--- [System] YouTube Live 24/7 is Starting ---")
    
    if not STREAM_KEY:
        print("--- [Error] STREAM_KEY is missing in GitHub Secrets! ---")
        return

    while True:
        # 1. توليد القصة بالذكاء الاصطناعي
        data = await fetch_story()
        if not data: 
            await asyncio.sleep(10)
            continue

        # 2. تحويل النص لصوت (سريع جداً)
        voice_file = "v.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(voice_file)

        # 3. جلب فيديو خلفية من Pexels
        video_file = "b0.mp4"
        p_url = f"https://api.pexels.com/videos/search?query=technology&per_page=1&orientation=landscape"
        res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
        if 'videos' in res:
            v_link = res['videos'][0]['video_files'][0]['link']
            with open(video_file, "wb") as f: f.write(requests.get(v_link).content)

        # 4. فلتر الـ 240p السحري (خفيف على السيرفر ومستقر في البث)
        # بيضيف شريط إعلاني متحرك لتطبيقاتك تحت
        filter_complex = (
            "[0:v]scale=426:240:force_original_aspect_ratio=decrease,pad=426:240:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
            f"[v0]drawtext=text='{MY_APPS}':fontcolor=white:fontsize=18:x=w-mod(t*50\,w+tw):y=h-30:box=1:boxcolor=black@0.6[finalv]"
        )

        # 5. أمر FFmpeg "الطلقة" لليوتيوب
        cmd = [
            "ffmpeg", "-re", "-y", "-i", video_file, "-i", voice_file,
            "-filter_complex", filter_complex,
            "-map", "[finalv]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", 
            "-r", "20", "-g", "40", "-b:v", "400k",
            "-c:a", "aac", "-b:a", "64k", "-ar", "44100",
            "-f", "flv", YOUTUBE_URL
        ]

        # تشغيل البث وانتظار انتهاء الفيديو الحالي قبل البدء في القصة التالية
        process = subprocess.run(cmd)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(broadcast())
