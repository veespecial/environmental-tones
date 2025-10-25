import requests
import time
import os
import json
from datetime import datetime
import pytz  # pip install pytz
import subprocess

# Stream URL
STREAM_URL = "https://listen.radioking.com/radio/493333/stream/550315"

# Paths
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_INDEX = os.path.join(REPO_DIR, "index.html")
PLAYLIST_JSON = os.path.join(REPO_DIR, "playlist.json")

# Song tracking
current_song = None
song_history = []

# Load playlist.json if exists
if os.path.exists(PLAYLIST_JSON):
    with open(PLAYLIST_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        current_song = f"{data['current']['title']}, by {data['current']['artist']}"
        song_history = [f"{s['title']}, by {s['artist']}" for s in data.get("recent", [])]

def fetch_song():
    try:
        r = requests.get(STREAM_URL, stream=True, headers={"Icy-MetaData": "1"}, timeout=10)
        if "icy-metaint" not in r.headers:
            return None
        meta_int = int(r.headers["icy-metaint"])
        stream = r.raw
        stream.read(meta_int)
        length_byte = stream.read(1)
        if not length_byte:
            return None
        metadata_length = int.from_bytes(length_byte, "big") * 16
        if metadata_length == 0:
            return None
        metadata = stream.read(metadata_length).decode("utf-8", errors="ignore")
        if "StreamTitle='" in metadata:
            song = metadata.split("StreamTitle='")[1].split("';")[0].strip()
            if " - " in song:
                artist, title = song.split(" - ", 1)
                return f"{title}, by {artist}"
            return song
        return None
    except Exception:
        return None

def write_page(now_playing, history, timestamp):
    lines = []
    lines.append(f"<b>Now on Environmental</b><br>{now_playing}<br><br>")
    lines.append("<b>The last ten songs on Environmental</b><br>")

    padded = history + ["---"] * (10 - len(history))
    padded = padded[:10]

    for i, song in enumerate(padded):
        lines.append(song)
        if i < len(padded) - 1:
            lines.append("<div style='height:1px;'>&#8203;</div>")
            lines.append("<img src='shimi.gif' height='3' width='1' style='display:block;margin:0;'>")

    # single line before timestamp
    lines.append("<div style='line-height:1em;'>&#8203;</div>")
    lines.append(f"<div id='update'>Updated: {timestamp}</div>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Refresh" content="180">
<title>Environmental - What's Playing Now</title>
<link rel="stylesheet" href="wpnpop.css" type="text/css" media="all">
</head>
<body>
<table width="300" border="0" align="center" cellpadding="5" cellspacing="4" bgcolor="#FFFFFF">
<tr>
<td bgcolor="#666666" align="center">
<img src="whatsplayingnow220.gif" width="220" height="40" alt="What's Playing Now">
</td>
</tr>
<tr>
<td>
<div id="titles">
{chr(10).join(lines)}
</div>
</td>
</tr>
<tr>
<td bgcolor="#666666" align="center">
<a href="javascript:self.close()">
<img src="close100.gif" width="100" height="19" border="0" alt="Close">
</a>
</td>
</tr>
</table>
</body>
</html>
"""
    with open(REPO_INDEX, "w", encoding="utf-8") as f:
        f.write(html)

def update_playlist_json(now_playing, history):
    current = {"title": now_playing.split(", by ")[0], "artist": now_playing.split(", by ")[1]}
    recent = [{"title": s.split(", by ")[0], "artist": s.split(", by ")[1]} for s in history]
    data = {"current": current, "recent": recent}
    with open(PLAYLIST_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def git_push():
    try:
        subprocess.run(["git", "add", "index.html", "playlist.json"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Update index.html and playlist.json"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print("Pushed updates to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"Git push failed: {e}")

def main_loop():
    global current_song, song_history
    eastern = pytz.timezone("US/Eastern")
    while True:
        song = fetch_song()
        if song and song != current_song:
            if current_song:
                song_history.insert(0, current_song)
                song_history = song_history[:10]
            current_song = song
            timestamp = datetime.now(eastern).strftime("%a %b %d %I:%M:%S %p EDT %Y")
            write_page(current_song, song_history, timestamp)
            update_playlist_json(current_song, song_history)
            git_push()
            print(f"Updated: {current_song} at {timestamp}")
        time.sleep(1)

if __name__ == "__main__":
    main_loop()
