import os
import requests
import random
import subprocess
import asyncio
import json
from groq import Groq
import edge_tts

# الإعدادات
GROQ_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

client = Groq(api_key=GROQ_KEY)

async def get_content():
    # اطلب من الذكاء الاصطناعي الخبر + كلمات البحث للفيديو + عنوان قصير للشاشة
    prompt = (
        "Give me a trending global tech news. "
        "Return ONLY a JSON object with these keys: "
        "'text' (the full news in 3 sentences), "
        "'search_query' (2 English words for Pexels video search), "
        "'headline' (5 words max for screen title)."
    )
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"} # لإجبار الذكاء الاصطناعي على رد منظم
    )
    
    data = json.loads(completion.choices[0].message.content)
    
    # تحويل النص لصوت (إنجليزي)
    communicate = edge_tts.Communicate(data['text'], "en-US-AndrewNeural")
    await communicate.save("voice.mp3")
    
    return data # نرجع كل البيانات (النص، الكلمات، العنوان)

def get_video(query):
    headers = {"Authorization": PEXELS_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5"
    r = requests.get(url, headers=headers).json()
    # اختيار فيديو عشوائي من النتائج لزيادة التنوع
    video_url = random.choice(r['videos'])['video_files'][0]['link']
    with open("bg_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)

def start_stream(headline):
    # إضافة العنوان (Headline) فوق الفيديو باستخدام فلاتر FFmpeg
    # سنضع خلفية سوداء شفافة خلف النص ليظهر بوضوح كقنوات الأخبار
    drawtext_filter = (
        f"drawtext=text='{headline}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.6:"
        f"boxborderw=10:x=(w-text_w)/2:y=h-60"
    )
    
    cmd = (
        f"ffmpeg -re -loop 1 -i bg_video.mp4 -i voice.mp3 "
        f"-vf \"scale=426:240,format=yuv420p,{drawtext_filter}\" "
        f"-c:v libx264 -preset ultrafast -r 24 -g 48 -b:v 400k "
        f"-c:a aac -b:a 64k -shortest -f flv {YOUTUBE_URL}"
    )
    subprocess.run(cmd, shell=True)

async def run_loop():
    while True:
        try:
            print("--- Generating New News Segment ---")
            data = await get_content()
            print(f"Topic: {data['headline']}")
            get_video(data['search_query'])
            start_stream(data['headline'])
        except Exception as e:
            print(f"Error: {e}. Retrying in 10s...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_loop())
