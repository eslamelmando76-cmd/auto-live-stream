name: 24/7 AI Story Stream

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  stream:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4 # تم تصحيح الـ action هنا
        with:
          python-version: '3.9'

      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Install Python Dependencies
        run: pip install -r requirements.txt

      - name: Run python main.py
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
          TWITCH_KEY: ${{ secrets.TWITCH_KEY }} # ده مفتاح يوتيوب اللي هتحطه في الـ Secrets
        run: python main.py
