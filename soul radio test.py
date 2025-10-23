import requests
import time
from datetime import datetime, timezone

# Environmental Tones RadioKing stream URL
stream_url = "https://listen.radioking.com/radio/712013/stream/777593"

# Track current song and history
last_song = None
song_history = []

# Output file
REPO_INDEX = "index.html"

def format_page(now_playing, history, timestamp):
    lines = []
    lines.append("Now on Environmental Tones")
    lines.append(now_playing if now_playing else "---")
    lines.append("")
    lines.append("The last ten songs on Environmental Tones")
    padded = history + ["---"] * (10 - len(history))
    for song in padded:
        lines.append(song)
        lines.append("")  # blank line between songs
    lines.append(f"Updated: {timestamp}")
    return "\n".join(lines)

def write_page(content):
    with open(REPO_INDEX, "w", encoding="utf-8") as f:
        f.write(f'<pre style="color: white; background: black;">\n{content}\n</pre>\n')
    print(f"Wrote index.html with update at {datetime.now().strftime('%H:%M:%S')}")

def fetch_metadata():
    global last_song, song_history
    try:
        r = requests.get(
            stream_url,
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
            if song:
                parts = song.split(" - ")
                if len(parts) == 2:
                    song = f"{parts[1]}, by {parts[0]}"
                if song != last_song:
                    if last_song:
                        song_history.insert(0, last_song)
                        song_history = song_history[:10]
                    last_song = song
                    return True
    except Exception:
        return False

def main():
    while True:
        try:
            changed = fetch_metadata()
            if changed:
                timestamp = datetime.now(timezone.utc).strftime("%a %b %d %I:%M:%S %p EDT %Y")
                content = format_page(last_song, song_history, timestamp)
                write_page(content)
            time.sleep(1)
        except Exception as e:
            print(f"Stream error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
