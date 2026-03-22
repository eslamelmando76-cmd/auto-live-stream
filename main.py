import os
import requests
import random
import subprocess
import asyncio
from groq import Groq
import edge_tts

# الإعدادات من Secrets
GROQ_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

client = Groq(api_key=GROQ_KEY)

async def get_content():
    # 1. توليد خبر تقني سريع من Groq
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "أعطني معلومة تقنية مذهلة وقصيرة جدا بالعربية للتوعية"}],
        model="llama3-8b-8192",
    )
    text = chat_completion.choices[0].message.content
    
    # 2. تحويل النص لصوت
    communicate = edge_tts.Communicate(text, "ar-EG-ShakirNeural")
    await communicate.save("voice.mp3")
    return "technology" # الكلمة المفتاحية للبحث عن فيديو

def get_video(query):
    # 3. جلب فيديو من Pexels
    headers = {"Authorization": PEXELS_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
    r = requests.get(url, headers=headers).json()
    video_url = r['videos'][0]['video_files'][0]['link']
    with open("bg_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)

def start_stream():
    # 4. البث باستخدام FFmpeg بجودة 240p و 24 إطار
    cmd = (
        "ffmpeg -re -loop 1 -i bg_video.mp4 -i voice.mp3 "
        "-vf 'scale=426:240,format=yuv420p' -c:v libx264 -preset ultrafast "
        "-r 24 -g 48 -b:v 400k -c:a aac -b:a 64k -shortest -f flv " + YOUTUBE_URL
    )
    subprocess.run(cmd, shell=True)

async def run():
    query = await get_content()
    get_video(query)
    start_stream()

if __name__ == "__main__":
    asyncio.run(run())
