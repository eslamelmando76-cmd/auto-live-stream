import os
import requests
import random
import subprocess
import asyncio
import json
from groq import Groq
import edge_tts

# 1. إعدادات الوصول (تأكد من إضافتها في GitHub Secrets)
GROQ_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

client = Groq(api_key=GROQ_KEY)

async def get_content():
    """توليد محتوى الخبر والبحث والعنوان من Groq AI"""
    print("--- Step 1: Generating News with Groq AI ---")
    prompt = (
        "Give me a trending global tech news. "
        "Return ONLY a JSON object with these keys: "
        "'text' (the full news in 3-4 clear sentences), "
        "'search_query' (2 precise English keywords for video search), "
        "'headline' (5-6 words max for the news ticker)."
    )
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", # الموديل الأحدث والمستقر
            response_format={"type": "json_object"}
        )
        data = json.loads(completion.choices[0].message.content)
        
        # تحويل النص لصوت إنجليزي احترافي (صوت Andrew)
        print(f"--- Step 2: Generating Audio for: {data['headline']} ---")
        communicate = edge_tts.Communicate(data['text'], "en-US-AndrewNeural")
        await communicate.save("voice.mp3")
        
        return data
    except Exception as e:
        print(f"Error in Groq/TTS: {e}")
        return None

def get_video(query):
    """جلب 3 مقاطع فيديو متنوعة من Pexels بناءً على الخبر"""
    print(f"--- Step 3: Fetching 3 Clips for '{query}' from Pexels ---")
    headers = {"Authorization": PEXELS_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15"
    
    try:
        r = requests.get(url, headers=headers).json()
        selected_videos = random.sample(r['videos'], 3)
        
        for i, vid in enumerate(selected_videos):
            video_url = vid['video_files'][0]['link']
            with open(f"part_{i}.mp4", "wb") as f:
                f.write(requests.get(video_url).content)
        return True
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return False

def start_stream(headline):
    """دمج المقاطع وإضافة الساعة وشريط الأخبار والبث لليوتيوب"""
    print("--- Step 4: Starting FFmpeg Live Stream ---")
    
    # فلتر معالجة الفيديو: دمج 3 فيديوهات + ساعة + شريط أخبار أحمر
    filter_complex = (
        "[0:v]scale=426:240,setsar=1[v0];"
        "[1:v]scale=426:240,setsar=1[v1];"
        "[2:v]scale=426:240,setsar=1[v2];"
        "[v0][v1][v2]concat=n=3:v=1:a=0[v_out];"
        # الساعة الرقمية (أعلى اليمين)
        "[v_out]drawtext=text='%{localtime\\:%H\\:%M\\:%S}':fontcolor=yellow:fontsize=16:x=w-text_w-10:y=10:box=1:boxcolor=black@0.5,"
        # شريط الأخبار العاجلة (أسفل المركز)
        f"drawtext=text='BREAKING NEWS | {headline.upper()}':fontcolor=white:fontsize=18:box=1:boxcolor=red@0.8:"
        f"boxborderw=10:x=(w-text_w)/2:y=h-45"
    )
    
    cmd = (
        f"ffmpeg -re -i part_0.mp4 -i part_1.mp4 -i part_2.mp4 -i voice.mp3 "
        f"-filter_complex \"{filter_complex}\" "
        f"-map \"[v_out]\" -map 3:a -c:v libx264 -preset ultrafast -r 24 -g 48 "
        f"-b:v 450k -c:a aac -b:a 64k -shortest -f flv {YOUTUBE_URL}"
    )
    
    subprocess.run(cmd, shell=True)

async def main_loop():
    """الحلقة اللانهائية للبث 24/7"""
    while True:
        data = await get_content()
        if data:
            success = get_video(data['search_query'])
            if success:
                start_stream(data['headline'])
        
        print("--- Segment Finished. Restarting Loop... ---")
        await asyncio.sleep(2) # راحة قصيرة قبل الخبر القادم

if __name__ == "__main__":
    asyncio.run(main_loop())
