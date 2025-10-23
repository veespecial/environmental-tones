import requests
import time
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo  # proper timezone handling

# Radio stream
STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"

# Git repo folder (should be the folder where template.htm lives)
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(REPO_PATH, "template.htm")
OUTPUT_FILE = os.path.join(REPO_PATH, "index.html")

# Track current and history
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

def update_template(current_song, history):
    # Read template
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_lines = f.read().splitlines()

    # Find placeholder lines (lines containing ", by ")
    placeholder_indices = [i for i, line in enumerate(template_lines) if ", by " in line]

    # Pad songs list to match number of placeholders
    padded_songs = [current_song] + history
    padded_songs += ["---"] * (len(placeholder_indices) - len(padded_songs))

    # Replace placeholders individually
    for idx, song in zip(placeholder_indices, padded_songs):
        template_lines[idx] = song

    # Update timestamp line
    now = datetime.now(ZoneInfo("America/New_York"))
    timestamp_str = now.strftime("%a %b %d %I:%M:%S %p %Z %Y")
    for i, line in enumerate(template_lines):
        if "Updated:" in line:
            template_lines[i] = f"Updated: {timestamp_str}"

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(template_lines))

    print(f"Wrote {OUTPUT_FILE} at {timestamp_str}")

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
                song_history = song_history[:10]  # Keep last 10 songs
            last_song = song

            update_template(last_song, song_history)
            git_commit_push()
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()
