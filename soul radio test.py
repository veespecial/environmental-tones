import os
import time
import requests
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo  # for proper EDT handling

STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(REPO_PATH, "template.htm")
OUTPUT_FILE = os.path.join(REPO_PATH, "index.html")

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
    out_lines = []
    song_placeholders = [i for i, line in enumerate(template_lines) if ", by " in line]

    # Replace placeholder songs with history
    songs_to_write = [now_playing] + history[:10]
    for i, idx in enumerate(song_placeholders):
        if i < len(songs_to_write):
            out_lines.append(template_lines[idx].replace(template_lines[idx], songs_to_write[i]))
        else:
            out_lines.append(template_lines[idx])

    # Insert the rest of template lines unchanged
    final_lines = []
    song_idx = 0
    for i, line in enumerate(template_lines):
        if i in song_placeholders:
            final_lines.append(out_lines[song_idx])
            song_idx += 1
        elif "Updated:" in line:
            now = datetime.now(ZoneInfo("America/New_York"))
            final_lines.append(f"Updated: {now.strftime('%a %b %d %I:%M:%S %p %Z %Y')}")
        else:
            final_lines.append(line)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))

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

    # Load template once
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
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
