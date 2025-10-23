import requests
import time
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

STREAM_URL = "https://listen.radioking.com/radio/712013/stream/777593"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
REPO_INDEX = os.path.join(REPO_PATH, "index.html")

# Load template once
TEMPLATE_FILE = os.path.join(REPO_PATH, "template.html")
with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    template_lines = f.readlines()

last_song = None
song_history = []

SONG_PLACEHOLDERS = [
    "IF WE FALL IN LOVE AGAIN, by Tom Kellock",
    "CHECK IT OUT, by Andre Mayeux",
    "TEARS FROM THE SUN, by PASERO/SUZUKI-HAWAII",
    "San Francisco (Be Sure To Wear...), by Harley Brothers",
    "I'M BEGINNING TO SEE THE LIGHT, by April Barrows",
    "Wayland, by Orchestre Philharmonique de Radio France/Paavo Jarvi",
    "SHE'S NO LADY, by North Point",
    "BACK TO LOVE, by Nick Manson",
    "Changes, by Ray Kelley",
    "I KNOW, by Harley",
]

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
            return metadata.split("StreamTitle='")[1].split("';")[0].strip()
    except Exception as e:
        print(f"Metadata error: {e}")
        return None

def write_page(template_lines, now_playing, history):
    lines = template_lines.copy()
    # Replace current song
    for i, placeholder in enumerate(SONG_PLACEHOLDERS):
        if i == 0 and now_playing:
            lines = [line.replace(placeholder, now_playing) if placeholder in line else line for line in lines]
        elif i-1 < len(history):
            lines = [line.replace(placeholder, history[i-1]) if placeholder in line else line for line in lines]
        else:
            lines = [line.replace(placeholder, "---") if placeholder in line else line for line in lines]

    # Update timestamp
    now = datetime.now(ZoneInfo("America/New_York"))
    timestamp_str = now.strftime("%a %b %d %I:%M:%S %p %Z %Y")
    lines = [line if "Updated:" not in line else f"Updated: {timestamp_str}\n" for line in lines]

    with open(REPO_INDEX, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote index.html at {timestamp_str}")

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
                song_history = song_history[:9]  # only 9 because current song is separate
            last_song = song
            write_page(template_lines, last_song, song_history)
            git_commit_push()
        time.sleep(5)

if __name__ == "__main__":
    main()
