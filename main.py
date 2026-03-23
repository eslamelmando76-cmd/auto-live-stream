import os
import requests
import random
import subprocess
import asyncio
import json
import edge_tts

# الإعدادات من GitHub Secrets
HF_TOKEN = os.getenv("HF_TOKEN")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
STREAM_KEY = os.getenv("STREAM_KEY")
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

# رابط موديل Llama 3 على Hugging Face
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

news_queue = [] # طابور الأخبار

async def fetch_news_batch():
    """طلب مجموعة أخبار في طلب واحد لتقليل الضغط على الـ API"""
    print("--- Fetching a new batch of tech news from Hugging Face ---")
    
    prompt = (
        "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
        "Generate 5 different trending tech news stories. "
        "Return ONLY a JSON array of 5 objects. Each object must have: "
        "'text' (3 sentences in English), 'search_query' (2 search words), 'headline' (5 words max). "
        "Strictly return valid JSON only.<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 1000, "return_full_text": False}})
        result = response.json()
        
        # Hugging Face يرجع النص أحياناً داخل قائمة
        content = result[0]['generated_text'] if isinstance(result, list) else result.get('generated_text', "")
        
        # استخراج الـ JSON وتنظيفه
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != -1:
            items = json.loads(content[start:end])
            return items
        return []
    except Exception as e:
        print(f"HF API Error: {e}")
        return []

async def process_segment(data):
    """معالجة خبر واحد وبثه باستخدام FFmpeg"""
    try:
        print(f"--- Processing News: {data['headline']} ---")
        # 1. تحويل النص لصوت
        communicate = edge_tts.Communicate(data['text'], "en-US-AndrewNeural")
        await communicate.save("voice.mp3")

        # 2. جلب فيديوهات من Pexels
        p_headers = {"Authorization": PEXELS_KEY}
        p_url = f"https://api.pexels.com/videos/search?query={data['search_query']}&per_page=10"
        r = requests.get(p_url, headers=p_headers).json()
        
        if 'videos' in r and len(r['videos']) >= 3:
            selected_vids = random.sample(r['videos'], 3)
            for i, v in enumerate(selected_vids):
                v_url = v['video_files'][0]['link']
                with open(f"part_{i}.mp4", "wb") as f:
                    f.write(requests.get(v_url).content)

            # 3. البث (FFmpeg)
            headline = data['headline'].replace("'", "").replace(":", "")
            filter_complex = (
                "[0:v]scale=426:240,setsar=1[v0];[1:v]scale=426:240,setsar=1[v1];[2:v]scale=426:240,setsar=1[v2];"
                "[v0][v1][v2]concat=n=3:v=1:a=0[vc];"
                "[vc]drawtext=text='%{localtime\\:%H\\:%M\\:%S}':fontcolor=yellow:fontsize=16:x=w-text_w-10:y=10:box=1:boxcolor=black@0.5[v_c];"
                f"[v_c]drawtext=text='LIVE NEWS | {headline.upper()}':fontcolor=white:fontsize=18:box=1:boxcolor=red@0.8:x=(w-text_w)/2:y=h-45[v_f]"
            )
            
            cmd = (
                f"ffmpeg -re -i part_0.mp4 -i part_1.mp4 -i part_2.mp4 -i voice.mp3 "
                f"-filter_complex \"{filter_complex}\" -map \"[v_f]\" -map 3:a -c:v libx264 "
                f"-preset ultrafast -r 24 -g 48 -b:v 450k -c:a aac -b:a 64k -shortest -f flv {YOUTUBE_URL}"
            )
            subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"Error in processing segment: {e}")

async def main_loop():
    global news_queue
    while True:
        if not news_queue:
            news_queue = await fetch_news_batch()
            if not news_queue:
                print("Queue is empty, waiting 60s...")
                await asyncio.sleep(60)
                continue
        
        current_news = news_queue.pop(0)
        await process_segment(current_news)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main_loop())
