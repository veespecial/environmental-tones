import requests
import time
import os
import subprocess
from datetime import datetime, timezone

# Radio stream
STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"

# Git repo folder (should be the current folder where index.html lives)
REPO_PATH = os.path.dirname(os.path.abspath(__file__))

# Track current and history
last_song = None
song_history = []

# Output file
REPO_INDEX = os.path.join(REPO_PATH, "index.html")

def format_page(now_playing, history, timestamp):
    lines = []
    lines.append("Now on Environmental Tones")
    lines.append(now_playing if now_playing else "---")
    lines.append("")
    lines.append("The last ten songs on Environmental Tones")
    padded = history + ["---"] * (10 - len(history))
    for song in padded:
        lines.append(song)
        lines.append("")
    lines.append(f"Updated: {timestamp}")
    return "\n".join(lines)

def write_page(content):
    with open(REPO_INDEX, "w", encoding="utf-8") as f:
        f.write(f'<pre style="color: white; background: black;">\n{content}\n</pre>\n')
    print(f"Wrote index.html with update at {datetime.now().strftime('%H:%M:%S')}")

def fetch_metadata():
    try:
        r = requests.get(
            STREAM_URL,
            stream=True,
            headers={"Icy-MetaData": "1"},
            timeout=10
        )
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
            return song
    except Exception as e:
        print(f"Metadata error: {e}")
        return None

def git_commit_push():
    try:
        subprocess.run(["git", "-C", REPO_PATH, "add", "."], check=True)
        subprocess.run(
            ["git", "-C", REPO_PATH, "commit", "-m", "Auto-update index.html"],
            check=True
        )
        subprocess.run(["git", "-C", REPO_PATH, "push", "origin", "main"], check=True)
        print("Pushed update to GitHub Pages.")
    except subprocess.CalledProcessError as e:
        print(f"Git push failed: {e}")

def main():
    global last_song, song_history
    while True:
        song = fetch_metadata()
        if song and song != last_song:
            if last_song:
                song_history.insert(0, last_song)
                song_history = song_history[:10]
            last_song = song
            timestamp = datetime.now(timezone.utc).strftime(
                "%a %b %d %I:%M:%S %p UTC %Y"
            )
            page_content = format_page(last_song, song_history, timestamp)
            write_page(page_content)
            git_commit_push()
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()
