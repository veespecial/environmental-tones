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
        lines = f.readlines()

    # Find placeholder lines (songs on template)
    # Assume placeholders are the lines between "Now on Environmental" and "Updated:"
    try:
        start_idx = next(i for i, line in enumerate(lines) if line.strip() == "Now on Environmental")
        end_idx = next(i for i, line in enumerate(lines) if line.strip().startswith("Updated:"))
    except StopIteration:
        print("Could not find placeholders in template.")
        return

    # Build replacement block
    replacement = [f"{current_song}\n"] if current_song else ["---\n"]
    padded_history = history + ["---"] * (10 - len(history))
    for song in padded_history[:10]:
        replacement.append(f"{song}\n")

    # Replace lines
    lines[start_idx + 1:end_idx] = replacement

    # Update timestamp
    now = datetime.now(ZoneInfo("America/New_York"))
    timestamp = now.strftime("%a %b %d %I:%M:%S %p %Z %Y")
    for i, line in enumerate(lines):
        if line.strip().startswith("Updated:"):
            lines[i] = f"Updated: {timestamp}\n"

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Updated {OUTPUT_FILE} at {timestamp}")

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
            update_template(last_song, song_history)
            git_commit_push()
        time.sleep(5)  # check every 5 seconds

if __name__ == "__main__":
    main()
