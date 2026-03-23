import os
import requests
import random
import subprocess
import asyncio
import json
import edge_tts

# الإعدادات
HF_TOKEN = os.getenv("HF_TOKEN")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# موديل سريع جداً ومتاح دائماً
API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

news_queue = []

async def fetch_news_batch():
    print("--- Requesting News Batch ---")
    prompt = "<|user|>\nGenerate 5 trending tech news stories. Return ONLY a JSON array of 5 objects: [{'text': '...', 'search_query': '...', 'headline': '...'}]. No extra text.<|assistant|>\n"
    try:
        response = requests.post(API_URL, headers=headers, json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 800}
        }, timeout=40)
        result = response.json()
        if isinstance(result, list):
            content = result[0].get('generated_text', "")
        else:
            content = result.get('generated_text', "")
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != -1:
            return json.loads(content[start:end])
        return []
    except Exception as e:
        print(f"Fetch Error: {e}")
        return []

async def process_segment(data):
    try:
        print(f"--- Live Now: {data['headline']} ---")
        communicate = edge_tts.Communicate(data['text'], "en-US-AndrewNeural")
        await communicate.save("voice.mp3")
        p_headers = {"Authorization": PEXELS_KEY}
        p_url = f"https://api.pexels.com/videos/search?query={data['search_query']}&per_page=10"
        r = requests.get(p_url, headers=p_headers).json()
        if 'videos' in r and len(r['videos']) >= 3:
            selected_vids = random.sample(r['videos'], 3)
            for i, v in enumerate(selected_vids):
                with open(f"part_{i}.mp4", "wb") as f:
                    f.write(requests.get(v['video_files'][0]['link']).content)
            headline = data['headline'].replace("'", "").replace(":", "")
            filter_complex = (
                "[0:v]scale=426:240,setsar=1[v0];[1:v]scale=426:240,setsar=1[v1];[2:v]scale=426:240,setsar=1[v2];"
                "[v0][v1][v2]concat=n=3:v=1:a=0[vc];"
                "[vc]drawtext=text='%{localtime\\:%H\\:%M\\:%S}':fontcolor=yellow:fontsize=16:x=w-text_w-10:y=10:box=1:boxcolor=black@0.5[v_c];"
                f"[v_c]drawtext=text='AI TECH NEWS | {headline.upper()}':fontcolor=white:fontsize=18:box=1:boxcolor=red@0.8:x=(w-text_w)/2:y=h-45[v_f]"
            )
            cmd = (
                f"ffmpeg -re -i part_0.mp4 -i part_1.mp4 -i part_2.mp4 -i voice.mp3 "
                f"-filter_complex \"{filter_complex}\" -map \"[v_f]\" -map 3:a -c:v libx264 "
                f"-preset ultrafast -r 24 -g 48 -b:v 450k -c:a aac -shortest -f flv {YOUTUBE_URL}"
            )
            subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"Segment Error: {e}")

async def main_loop():
    global news_queue
    while True:
        if not news_queue:
            news_queue = await fetch_news_batch()
            if not news_queue:
                await asyncio.sleep(20)
                continue
        current_news = news_queue.pop(0)
        await process_segment(current_news)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main_loop())
