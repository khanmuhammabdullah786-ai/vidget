"""
VidGet backend — real downloader server (yt-dlp based).
Run:  pip install flask yt-dlp
       python app.py
Then open http://localhost:5000 and paste any social media link.

Supports: YouTube, TikTok, Instagram, Facebook, X/Twitter, Snapchat,
Reddit, Pinterest, Vimeo, Dailymotion, Twitch and 1000+ sites yt-dlp knows.
Legal note: only download videos you own or have permission to download.
"""
import os
import re
import uuid
import threading
from flask import Flask, request, jsonify, send_file, abort

app = Flask(__name__)
DOWNLOADS = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS, exist_ok=True)

PLATFORMS = [
    ("youtube.com", "YouTube"), ("youtu.be", "YouTube"),
    ("tiktok.com", "TikTok"),
    ("instagram.com", "Instagram"),
    ("facebook.com", "Facebook"), ("fb.watch", "Facebook"),
    ("twitter.com", "X (Twitter)"), ("x.com", "X (Twitter)"),
    ("snapchat.com", "Snapchat"),
    ("reddit.com", "Reddit"),
    ("pinterest.com", "Pinterest"),
    ("vimeo.com", "Vimeo"),
    ("dailymotion.com", "Dailymotion"),
    ("twitch.tv", "Twitch"),
]

def detect_platform(url):
    for domain, name in PLATFORMS:
        if domain in url:
            return name
    return "Other"

def _cookiefile():
    """Login wale platforms ke liye cookies (koi aik):
    1) cookies.txt (local, app.py ke saath) ya
    2) YTDL_COOKIES_B64 env var (base64, Render dashboard mein PRIVATE) ya
    3) YTDL_COOKIES_TEXT env var (cookies.txt ka seedha text, Render
       dashboard mein PRIVATE — kabhi public repo mein cookies mat daalna,
       sab dekh lenge)."""
    local = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if os.path.exists(local):
        return local
    b64 = os.environ.get("YTDL_COOKIES_B64")
    if b64:
        try:
            import base64
            path = "/tmp/vidget-cookies.txt"
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            return path
        except Exception:
            pass
    text = os.environ.get("YTDL_COOKIES_TEXT")
    if text:
        try:
            path = "/tmp/vidget-cookies.txt"
            with open(path, "w") as f:
                f.write(text)
            return path
        except Exception:
            return None
    return None

def ydl_opts(quality, job_id, android=False):
    out = os.path.join(DOWNLOADS, job_id, "%(title)s.%(ext)s")
    base = {
        "outtmpl": out,
        "quiet": True,
        "no_warnings": True,
        "restrict_filenames": True,
    }
    if android:
        # YouTube ka web client kabhi timeout deta hai; android client
        # us waqt bhi chalta hai — is liye fallback ke tor par use hota hai.
        base["extractor_args"] = {"youtube": {"player_client": ["android"]}}
    cookiefile = _cookiefile()
    if cookiefile:
        base["cookiefile"] = cookiefile
    if quality == "mp3":
        base["format"] = "bestaudio/best"
        base["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif quality in ("2160p", "4k"):
        base["format"] = "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
        base["merge_output_format"] = "mp4"
    elif quality == "1080p":
        base["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        base["merge_output_format"] = "mp4"
    elif quality == "720p":
        base["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        base["merge_output_format"] = "mp4"
    elif quality == "480p":
        base["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]"
        base["merge_output_format"] = "mp4"
    else:  # best
        base["format"] = "bestvideo+bestaudio/best"
        base["merge_output_format"] = "mp4"
    return base

jobs = {}

def run_download(job_id, url, quality):
    import yt_dlp
    jobs[job_id] = {"status": "downloading"}
    last_error = None
    for android in (False, True):
        try:
            with yt_dlp.YoutubeDL(ydl_opts(quality, job_id, android=android)) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "video")
            folder = os.path.join(DOWNLOADS, job_id)
            files = [f for f in os.listdir(folder) if not f.startswith(".")]
            if not files:
                raise RuntimeError("No file produced")
            jobs[job_id] = {"status": "done", "title": title, "file": files[0]}
            return
        except Exception as e:  # noqa: BLE001 - pehle web, phir android client
            last_error = e
    jobs[job_id] = {"status": "error", "error": str(last_error)}

@app.route("/")
def home():
    """Poora tool aik jagah: page + download API (localhost:5000 kholo)."""
    return send_file(os.path.join(os.path.dirname(__file__), "index.html"))

@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Valid link daalein (http/https)"}), 400
    import yt_dlp
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            meta = ydl.extract_info(url, download=False)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Link read nahi ho saka: {e}"}), 400
    return jsonify({
        "platform": detect_platform(url),
        "title": meta.get("title"),
        "uploader": meta.get("uploader"),
        "duration": meta.get("duration"),
        "thumbnail": meta.get("thumbnail"),
    })

@app.route("/api/direct", methods=["POST"])
def direct():
    """Foran download: video ki direct file URL wapas karta hai, taake
    browser ka download foran shuru ho jaye — server par pehle poori
    file utarne ka wait nahi karna parta. Jo quality single file mein
    maujood na ho (jaise YouTube 1080p+/4K, jo alag video+audio
    streams hain), us ke liye needs_merge=true milta hai aur UI
    /api/download wale (server merge) raste par chali jati hai."""
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = data.get("quality", "720p")
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Valid link daalein (http/https)"}), 400
    heights = {"2160p": 2160, "4k": 2160, "1080p": 1080, "720p": 720, "480p": 480}
    if quality == "mp3":
        fmt = "bestaudio/best"
    elif quality in heights:
        h = heights[quality]
        # Single combined file (foran browser download ke liye behtareen)
        fmt = f"best[height<={h}][ext=mp4]/best[height<={h}]/best"
    else:
        fmt = "best"
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "format": fmt}
    cookiefile = _cookiefile()
    if cookiefile:
        opts["cookiefile"] = cookiefile
    info = None
    last_error = None
    for android in (False, True):
        try:
            o = dict(opts)
            if android:
                o["extractor_args"] = {"youtube": {"player_client": ["android"]}}
            with yt_dlp.YoutubeDL(o) as ydl:
                info = ydl.extract_info(url, download=False)
            break
        except Exception as e:  # noqa: BLE001 - pehle web, phir android client
            last_error = e
    if info is None:
        return jsonify({"error": f"Direct link nahi mila: {last_error}"}), 400
    direct_url = info.get("url")
    if not direct_url:
        # Alag video+audio streams: browser aik file ki tarah nahi utar sakta
        return jsonify({"needs_merge": True, "title": info.get("title")})
    ext = info.get("ext", "mp4")
    title = re.sub(r'[\\/*?:"<>|]', "", info.get("title", "video"))[:80]
    return jsonify({
        "direct_url": direct_url,
        "filename": f"{title}.{ext}",
        "title": info.get("title"),
        "platform": detect_platform(url),
    })

@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = data.get("quality", "720p")
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Valid link daalein (http/https)"}), 400
    if quality not in ("2160p", "4k", "1080p", "720p", "480p", "mp3", "best"):
        quality = "720p"
    job_id = uuid.uuid4().hex[:12]
    os.makedirs(os.path.join(DOWNLOADS, job_id), exist_ok=True)
    threading.Thread(target=run_download, args=(job_id, url, quality), daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def status(job_id):
    if not re.fullmatch(r"[0-9a-f]{12}", job_id or ""):
        abort(404)
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "pending"})
    return jsonify(job)

@app.route("/api/file/<job_id>")
def file(job_id):
    if not re.fullmatch(r"[0-9a-f]{12}", job_id or ""):
        abort(404)
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        abort(404)
    return send_file(os.path.join(DOWNLOADS, job_id, job["file"]), as_attachment=True)

if __name__ == "__main__":
    # Render/Railway jaise hosts PORT env var dete hain; local par 5000.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
