import requests
import time
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

# Radio stream
STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"

# Paths
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(REPO_PATH, "template.htm")
OUTPUT_PATH = os.path.join(REPO_PATH, "index.html")

# Track current and history
last_song = None
song_history = []

# How many songs to show
HISTORY_COUNT = 10

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

def write_page(template_lines, current_song, history):
    out_lines = []
    i = 0
    n = len(template_lines)

    while i < n:
        line = template_lines[i]

        # Replace current song
        if line.strip() == "Now on Environmental":
            out_lines.append(line)
            i += 1
            out_lines.append(current_song if current_song else "---")
            i += 1
            continue

        # Replace last 10 songs block
        if line.strip() == "The last ten songs on Environmental":
            out_lines.append(line)
            i += 1
            for j in range(HISTORY_COUNT):
                song_line = history[j] if j < len(history) else "---"
                out_lines.append(song_line)
                out_lines.append("")  # preserve spacing
            # Skip over old placeholder lines (guess 2 * HISTORY_COUNT lines)
            skip_count = 0
            while skip_count < HISTORY_COUNT * 2 and i < n:
                if template_lines[i].strip() == "":
                    skip_count += 1
                else:
                    skip_count += 1
                i += 1
            continue

        # Everything else
        out_lines.append(line)
        i += 1

    # Add updated timestamp at the end (replace any existing "Updated:")
    for idx, l in enumerate(out_lines):
        if l.startswith("Updated:"):
            out_lines[idx] = f"Updated: {datetime.now(ZoneInfo('America/New_York')).strftime('%a %b %d %I:%M:%S %p %Z %Y')}"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print(f"Wrote index.html at {datetime.now().strftime('%H:%M:%S')}")

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
    # Read template once
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_lines = f.read().splitlines()

    while True:
        song = fetch_metadata()
        if song and song != last_song:
            if last_song:
                song_history.insert(0, last_song)
                song_history = song_history[:HISTORY_COUNT]
            last_song = song
            write_page(template_lines, last_song, song_history)
            git_commit_push()
        time.sleep(5)

if __name__ == "__main__":
    main()
