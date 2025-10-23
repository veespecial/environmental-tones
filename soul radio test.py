import requests
import time
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo  # proper timezone handling

# Radio stream
STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"

# Paths
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(REPO_PATH, "template.htm")
OUTPUT_FILE = os.path.join(REPO_PATH, "index.html")

# Track current song and history
last_song = None
song_history = []

def fetch_metadata():
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
            return song
    except Exception as e:
        print(f"Metadata error: {e}")
        return None

def update_template(now_playing, history):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    padded_history = history + ["---"] * (10 - len(history))
    song_lines = [now_playing] + padded_history

    updated_lines = []
    song_idx = 0
    for line in lines:
        if '", by "' in line:
            if song_idx < len(song_lines):
                newline = "\n" if line.endswith("\n") else ""
                updated_lines.append(f"{song_lines[song_idx]}{newline}")
                song_idx += 1
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    now = datetime.now(ZoneInfo("America/New_York"))
    timestamp = now.strftime("%a %b %d %I:%M:%S %p %Z %Y")
    for i, line in enumerate(updated_lines):
        if line.lower().startswith("updated:"):
            updated_lines[i] = f"Updated: {timestamp}\n"
            break
    else:
        updated_lines.append(f"\nUpdated: {timestamp}\n")

    return updated_lines

def write_page(lines):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote {OUTPUT_FILE} at {datetime.now().strftime('%H:%M:%S')}")

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
    while True:
        song = fetch_metadata()
        if song and song != last_song:
            if last_song:
                song_history.insert(0, last_song)
                song_history = song_history[:10]
            last_song = song

            updated_lines = update_template(last_song, song_history)
            write_page(updated_lines)
            git_commit_push()
        time.sleep(5)

if __name__ == "__main__":
    main()
