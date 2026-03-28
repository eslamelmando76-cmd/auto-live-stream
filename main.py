import os, requests, subprocess, asyncio, json, edge_tts, random

# --- [الإعدادات الجاهزة لليوتيوب] ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
MY_APPS = "Download our Apps: Luxury Estate Guide on Play Store!"

# قائمة المواضيع لضمان عدم التكرار نهائياً
TOPICS = ["Cybersecurity Mystery", "AI Rebellion", "Deep Web Horror love", "love Future Space Tech", "love Time Travel Paradox", "Dark Web Secrets love"]

async def prepare_next_story(index):
    topic = random.choice(TOPICS)
    print(f"--- [System] Preparing next story about: {topic} ---")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # برومبت ذكي يطلب قصة وكلمات بحث للفيديو
    prompt = f"Write a 1600-word {topic} story. Return JSON: {{'title': '...', 'story': '...', 'queries': ['{topic.split()[0].lower()}']}}"
    
    try:
        # 1. جلب القصة من Groq
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=25).json()
        data = json.loads(r['choices'][0]['message']['content'])
        
        # 2. توليد الصوت (ملفات متبادلة v_0 و v_1 لمنع التقطيع)
        v_file = f"v_{index}.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(v_file)
        
        # 3. جلب فيديو من Pexels
        query = random.choice(data.get('queries', ['technology']))
        p_url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=landscape"
        res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()
        
        vid_file = f"b_{index}.mp4"
        if 'videos' in res and len(res['videos']) > 0:
            v_link = random.choice(res['videos'])['video_files'][0]['link']
            with open(vid_file, "wb") as f:
                f.write(requests.get(v_link).content)
                short_vid = f"short_{index}.mp4"
                subprocess.run([
        "ffmpeg", "-i", vid_file, "-t", "30", "-c", "copy", short_vid
   
           return vid_file, v_file, data['title']
    except Exception as e:
        print(f"Error in prepare_next_story: {e}")
        return None

async def broadcast():
    print("--- [System] Starting 24/7 Professional AI Stream ---")
    if not STREAM_KEY:
        print("--- [Error] STREAM_KEY is missing! ---")
        return

    current_idx = 0
    # تجهيز أول قصة قبل البث
    next_story = await prepare_next_story(current_idx)

    while True:
        if not next_story:
            await asyncio.sleep(5)
            next_story = await prepare_next_story(current_idx)
            continue
            
        vid, aud, title = next_story
        
        # التجهيز للقصة القادمة "في الخلفية" (بينما الحالية تذاع)
        current_idx = 1 - current_idx
        prepare_task = asyncio.create_task(prepare_next_story(current_idx))

     

        cmd = [
             "ffmpeg", "-stream_loop", "-1", "-re", "-y", "-i", vid,
             "-stream_loop", "-1", "-i", aud,
             "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
             "-r", "24", 
             "-b:v", "400k", "-maxrate", "450k", "-bufsize", "1200k",
             "-c:a", "aac", "-b:a", "64k", "-ar", "44100",
             "-shortest",
             "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2",
             "-f", "flv", YOUTUBE_URL
        ]

        # تشغيل FFmpeg وانتظار انتهاء القصة الحالية
        process = subprocess.Popen(cmd)
        
        # انتظار تجهيز القصة القادمة
        next_story = await prepare_task
        


if __name__ == "__main__":
    asyncio.run(broadcast())
