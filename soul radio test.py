import requests
import time
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import re

STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(REPO_PATH, "template.htm")
OUTPUT_PATH = os.path.join(REPO_PATH, "index.html")

last_song = None
song_history = []

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

def write_page(template_lines, now_playing, history):
    # Find the index of placeholders
    song_lines_idx = [i for i, l in enumerate(template_lines) if ", by " in l or l.strip() == "---"]

    # Prepare replacement lines
    new_block = [now_playing] + history
    new_block += ["---"] * (len(song_lines_idx) - len(new_block))  # pad to fit original template

    # Replace each line individually
    for idx, new_line in zip(song_lines_idx, new_block):
        template_lines[idx] = new_line

    # Update timestamp
    timestamp = datetime.now(ZoneInfo("America/New_York")).strftime("%a %b %d %I:%M:%S %p %Z %Y")
    for i, line in enumerate(template_lines):
        if "Updated:" in line:
            template_lines[i] = f"Updated: {timestamp}"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(template_lines))
    print(f"Wrote index.html at {timestamp}")

def git_commit_push():
    try:
        subprocess.run(["git", "-C", REPO_PATH, "add", "."], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "commit", "-m", "Auto-update index.html"], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "push", "origin", "main"], check=True)
        print("Pushed update to GitHub Pages.")
    except subprocess.CalledProcessError as e:
        print(f"Git push failed: {e}")

def main():
    global last_song, song_history
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_lines = f.read().splitlines()

    while True:
        song = fetch_metadata()
        if song and song != last_song:
            if last_song:
                song_history.insert(0, last_song)
                song_history = song_history[:10]
            last_song = song

            write_page(template_lines, last_song, song_history)
            git_commit_push()
        time.sleep(5)

if __name__ == "__main__":
    main()
