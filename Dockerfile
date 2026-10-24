# VidGet backend — Docker image (ffmpeg ke saath, taake MP3 aur
# HD merge har server par chale; Render is Dockerfile ko khud pehchan lega)
FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py index.html README.md ./

CMD ["python3", "app.py"]
