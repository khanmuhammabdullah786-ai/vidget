# VidGet — Social Media Video Downloader

Link paste karo, quality chuno (4K, 1080p HD, 720p, 480p, ya MP3 audio),
aur video download karo. YouTube, TikTok, Instagram, Facebook, X/Twitter,
Snapchat, Reddit, Pinterest, Vimeo, Dailymotion, Twitch aur 1000+ sites.

## Chalane ka tareeqa (apne computer/server par)

```bash
pip install flask yt-dlp
python3 app.py
```

Phir browser mein kholo: **http://localhost:5000**

> Note: `ffmpeg` bhi install hona chahiye (MP3 aur HD merge ke liye).
> Ubuntu: `sudo apt install ffmpeg` · Mac: `brew install ffmpeg`

## API

| Endpoint | Kaam |
|---|---|
| `POST /api/info` `{url}` | Video ka title, platform, thumbnail |
| `POST /api/direct` `{url, quality}` | **Foran download:** video ki direct file URL — browser ka download foran shuru, server par wait nahi |
| `POST /api/download` `{url, quality}` | Download shuru (server merge ke saath), `job_id` milta hai |
| `GET /api/status/<job_id>` | Download ki halat |
| `GET /api/file/<job_id>` | Tayar file download karo |

Quality values: `2160p` (4K), `1080p`, `720p`, `480p`, `mp3`, `best`

## Zaroori baat

Sirf wo videos download karein jin ke aap malik hain ya jin ki
ijazat hai. YouTube aur baqi platforms ki terms ka khayal rakhein.

## Live server par chalana (publish ke liye)

Apne computer par to `python3 app.py` se `http://localhost:5000` par
poora tool chal jata hai. Duniya ke liye live karne ka aasan tareeqa:

**Render (free) — 5 minute:**
1. Ye folder GitHub par daalein.
2. Render.com par "New Web Service" → repo chunein.
3. Build command: `pip install -r requirements.txt`
   Start command: `gunicorn app:app` (pehle `pip install gunicorn`
   karke requirements.txt mein daal dein) — ya seedha
   `python3 app.py` (chhote use ke liye theek hai).
4. Deploy hote hi aik public URL mil jayega — wohi aap ki site ka
   asli address hoga, aur usi par Meta ads chala sakenge.

**VPS (apna server ho to):**
```bash
pip install flask yt-dlp gunicorn
gunicorn -b 0.0.0.0:5000 app:app
```
Phir domain ko us server ki taraf point kar dein.

## Meta ads ki tayyari

- Site mein Meta Pixel ki jagah pehle se rakhi hui hai
  (`index.html` mein comment ki hui line) — apni Pixel ID daalte hi
  ads ki tracking shuru ho jayegi.
- Publish ke baad: Meta Ads Manager mein campaign banayein,
  destination mein site ka public URL dein.
- Ads ke liye zaroori cheezein: aik public URL, aik Meta Page
  (ads account se jura hua), aur Pixel ID — teeno milte hi ads live
  ho sakte hain.
