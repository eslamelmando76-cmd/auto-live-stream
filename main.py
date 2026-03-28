import os, requests, subprocess, asyncio, json, edge_tts, random

# --- إعدادات البث ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

TOPICS = [
    "Cybersecurity Mystery",
    "AI Rebellion",
    "Deep Web Horror",
    "Future Space Tech",
    "Time Travel Paradox",
    "Dark Web Secrets"
]

# --- تجهيز القصة ---
async def prepare_next_story(index):
    topic = random.choice(TOPICS)
    print(f"[System] Preparing next story about: {topic}")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Write a 300-word {topic} story. Return JSON: {{'title': '...', 'story': '...', 'queries': ['{topic.split()[0].lower()}']}}"

    try:
        r = requests.post(url, headers=headers, json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }, timeout=25).json()

        data = json.loads(r['choices'][0]['message']['content'])

        # توليد الصوت
        v_file = f"v_{index}.mp3"
        await edge_tts.Communicate(data['story'], "en-US-ChristopherNeural").save(v_file)

        # جلب فيديو من Pexels
        query = random.choice(data.get('queries', ['technology']))
        p_url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=landscape"
        res = requests.get(p_url, headers={"Authorization": PEXELS_KEY}).json()

        vid_file = f"b_{index}.mp4"
        if 'videos' in res and len(res['videos']) > 0:
            v_link = random.choice(res['videos'])['video_files'][0]['link']
            with open(vid_file, "wb") as f:
                f.write(requests.get(v_link).content)

            # قص الفيديو لمدته 30 ثانية
            short_vid = f"short_{index}.mp4"
            subprocess.run([
                "ffmpeg", "-i", vid_file, "-t", "30", "-c", "copy", short_vid
            ])

            return short_vid, v_file, data['title']

    except Exception as e:
        print(f"Error in prepare_next_story: {e}")
        return None

# --- البث ---
async def broadcast():
    print("[System] Starting 24/7 AI Stream...")
    if not STREAM_KEY:
        print("[Error] STREAM_KEY is missing!")
        return

    current_idx = 0
    next_story = await prepare_next_story(current_idx)

    while True:
        if not next_story:
            await asyncio.sleep(5)
            next_story = await prepare_next_story(current_idx)
            continue

        vid, aud, title = next_story
        current_idx = 1 - current_idx
        prepare_task = asyncio.create_task(prepare_next_story(current_idx))

        cmd = [
            "ffmpeg", "-stream_loop", "-1", "-re", "-y", "-i", vid,
            "-stream_loop", "-1", "-i", aud,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-r", "24",  # تثبيت معدل الإطارات
            "-b:v", "800k", "-maxrate", "850k", "-bufsize", "2400k",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-shortest",
            "-f", "flv", YOUTUBE_URL
        ]

        process = subprocess.Popen(cmd)
        next_story = await prepare_task
        process.wait()

if __name__ == "__main__":
    asyncio.run(broadcast())
