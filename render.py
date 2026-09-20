#!/usr/bin/env python3
"""
Render a sleep-meditation script to a narration track.

Speech is generated one line at a time by ElevenLabs. Every silence in the
finished track is built locally, because no TTS reliably produces a 40-second
pause -- asked for one, it invents breath, filler or a clipped tail.

Each rendered line is trimmed of its own leading and trailing silence before
assembly, so the [P n] marks in the script are the actual gaps in the output.

Consecutive lines are stitched with previous_request_ids, which keeps prosody
continuous across separate API calls. Renders are cached on disk by content
hash, so re-running after changing one line only bills for that line.

Usage
    python render.py --dry-run                     # parse + timing, no API calls
    python render.py --list-voices                 # names and ids on the account
    python render.py --movement 1 --out audition.wav
    python render.py --out narration.wav

Environment
    ELEVENLABS_API_KEY   required unless --dry-run
    ELEVENLABS_VOICE_ID  default voice, overridable with --voice

    Both are read from a .env file beside this script if one exists, so the
    key does not have to be exported in every shell. A real environment
    variable always wins over the file. .env is gitignored: the key belongs
    on your machine, never in the repo. See .env.example.

    --voice accepts either a voice id or a voice name as it appears in the
    ElevenLabs library; a name is resolved to an id before rendering.

Requires: requests, pydub, and ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
VOICES_URL = "https://api.elevenlabs.io/v1/voices"

# Credentials are read from here when they are not already in the environment.
ENV_FILE = Path(__file__).resolve().parent / ".env"

# eleven_multilingual_v2 is the stable long-form model. The expressive models
# carry more prosodic variance per call, and variance at 3am is a wake trigger.
DEFAULT_MODEL = "eleven_multilingual_v2"

# mp3_44100_128 works on every paid tier. mp3_44100_192 needs Creator or above;
# pcm_44100 and wav need Pro or above.
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"

DEFAULT_VOICE_SETTINGS = {
    "stability": 0.75,          # high: we want boring in the good way
    "similarity_boost": 0.75,
    "style": 0.0,               # zero: no performance, no emphasis hunting
    "use_speaker_boost": False,
}

PAUSE_RE = re.compile(r"^\[P\s+(\d+(?:\.\d+)?)\]$")
MOVEMENT_RE = re.compile(r"^##\s*(.+)$")

# Words per minute used only by --dry-run to project runtime. Measured pace for
# this register is 78-85; 82 is the middle.
DEFAULT_WPM = 82.0

MISSING_KEY = (
    "No ELEVENLABS_API_KEY.\n"
    "Put it in .env beside this script (see .env.example), or export it in\n"
    "your shell. .env is gitignored."
)

MISSING_VOICE = (
    "No voice. Put ELEVENLABS_VOICE_ID in .env, or pass --voice with an id\n"
    "or a voice name. Run --list-voices to see what is on the account."
)

MAX_STITCH_IDS = 3              # API accepts at most 3 previous_request_ids
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class Segment:
    kind: str                   # "speech" | "pause"
    movement: str
    index: int
    text: str = ""
    seconds: float = 0.0
    rendered_ms: int = 0
    request_id: str | None = None
    cached: bool = False


@dataclass
class Script:
    segments: list[Segment] = field(default_factory=list)

    @property
    def speech(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "speech"]

    @property
    def characters(self) -> int:
        return sum(len(s.text) for s in self.speech)


def parse_script(path: Path) -> Script:
    """Turn the script file into an ordered list of speech and pause segments."""
    script = Script()
    movement = "(unlabelled)"
    index = 0

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue

        heading = MOVEMENT_RE.match(line)
        if heading:
            movement = heading.group(1).strip()
            continue

        if line.startswith("#"):
            continue

        pause = PAUSE_RE.match(line)
        if pause:
            script.segments.append(
                Segment(kind="pause", movement=movement, index=index,
                        seconds=float(pause.group(1)))
            )
            index += 1
            continue

        if "[P" in line:
            raise ValueError(
                f"{path}:{lineno}: a [P n] mark must sit alone on its own line"
            )

        script.segments.append(
            Segment(kind="speech", movement=movement, index=index, text=line)
        )
        index += 1

    if not script.speech:
        raise ValueError(f"{path}: no speech lines found")
    return script


def load_dotenv(path: Path = ENV_FILE) -> None:
    """Read KEY=value lines from .env into the environment.

    A variable already set in the real environment is left alone, so an
    export in the shell still overrides the file. Called before the argument
    parser is built, because --voice defaults off ELEVENLABS_VOICE_ID.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def fetch_voices(api_key: str) -> list[dict]:
    """Every voice available to the account."""
    import requests

    response = requests.get(VOICES_URL, headers={"xi-api-key": api_key},
                            timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs returned {response.status_code} listing voices: "
            f"{response.text[:400]}"
        )
    return response.json().get("voices", [])


def print_voices(voices: list[dict]) -> None:
    if not voices:
        print("No voices on this account.")
        return
    width = max(len(v.get("name", "")) for v in voices)
    print(f"{'NAME'.ljust(width)}  VOICE ID                  CATEGORY")
    for voice in voices:
        print(f"{voice.get('name', '').ljust(width)}  "
              f"{voice.get('voice_id', ''):<24}  "
              f"{voice.get('category', '')}")
    print("\nPut the id you want in .env as ELEVENLABS_VOICE_ID, "
          "or pass --voice.")


def resolve_voice(wanted: str, api_key: str) -> str:
    """Accept a voice id or a voice name and return the id.

    Voice ids are opaque, so anything that is not an exact id match is looked
    up by name. Matching is case-insensitive; an ambiguous name is an error
    rather than a coin flip, because the wrong voice is 24 minutes of wasted
    credit and a re-render.
    """
    voices = fetch_voices(api_key)
    by_id = {v.get("voice_id", ""): v for v in voices}
    if wanted in by_id:
        return wanted

    hits = [v for v in voices if v.get("name", "").strip().lower() == wanted.strip().lower()]
    if not hits:
        hits = [v for v in voices if wanted.strip().lower() in v.get("name", "").lower()]

    if len(hits) == 1:
        voice = hits[0]
        print(f"Voice: {voice.get('name')} ({voice.get('voice_id')})")
        return voice["voice_id"]

    if not hits:
        raise SystemExit(
            f"No voice matches {wanted!r}. Run --list-voices to see the account."
        )
    names = ", ".join(f"{v.get('name')} ({v.get('voice_id')})" for v in hits)
    raise SystemExit(f"{wanted!r} matches more than one voice: {names}")


def cache_key(text: str, prev_text: str, next_text: str, voice_id: str,
              model: str, settings: dict, output_format: str) -> str:
    payload = json.dumps(
        {
            "text": text,
            "previous_text": prev_text,
            "next_text": next_text,
            "voice_id": voice_id,
            "model": model,
            "settings": settings,
            "output_format": output_format,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def tts(session, text: str, prev_text: str, next_text: str,
        prev_request_ids: list[str], voice_id: str, model: str,
        settings: dict, output_format: str, api_key: str,
        attempts: int = 4) -> tuple[bytes, str | None]:
    """One line of speech. Returns (audio bytes, request id for stitching)."""
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": settings,
    }
    if prev_text:
        body["previous_text"] = prev_text
    if next_text:
        body["next_text"] = next_text
    if prev_request_ids:
        # previous_request_ids supersedes previous_text when both are sent.
        body["previous_request_ids"] = prev_request_ids[-MAX_STITCH_IDS:]

    url = API_URL.format(voice_id=voice_id)
    # enable_logging stays on: zero-retention mode disables request stitching.
    params = {"output_format": output_format}
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    for attempt in range(1, attempts + 1):
        response = session.post(url, params=params, headers=headers,
                                json=body, timeout=120)
        if response.status_code == 200:
            request_id = (response.headers.get("request-id")
                          or response.headers.get("x-request-id"))
            return response.content, request_id

        if response.status_code in RETRY_STATUS and attempt < attempts:
            backoff = 2 ** attempt
            print(f"    {response.status_code}, retrying in {backoff}s "
                  f"({attempt}/{attempts - 1})", file=sys.stderr)
            time.sleep(backoff)
            continue

        raise RuntimeError(
            f"ElevenLabs returned {response.status_code}: {response.text[:400]}"
        )
    raise RuntimeError("unreachable")


def trim_silence(audio, threshold_db: float = -50.0):
    """Strip the model's own lead-in and tail so our pause marks are exact."""
    from pydub.silence import detect_leading_silence

    lead = detect_leading_silence(audio, silence_threshold=threshold_db, chunk_size=5)
    tail = detect_leading_silence(audio.reverse(), silence_threshold=threshold_db,
                                  chunk_size=5)
    if lead + tail >= len(audio):
        return audio                      # all quiet: leave it alone
    return audio[lead:len(audio) - tail]


def render(script: Script, args, api_key: str) -> None:
    import requests
    from pydub import AudioSegment

    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    speech = script.speech
    texts = [s.text for s in speech]
    stitch_ids: list[str] = []
    audio_by_index: dict[int, AudioSegment] = {}

    for position, segment in enumerate(speech):
        prev_text = texts[position - 1] if position > 0 else ""
        next_text = texts[position + 1] if position + 1 < len(texts) else ""
        key = cache_key(segment.text, prev_text, next_text, args.voice,
                        args.model, DEFAULT_VOICE_SETTINGS, args.output_format)
        audio_path = cache_dir / f"{key}.mp3"
        meta_path = cache_dir / f"{key}.json"

        if audio_path.exists():
            segment.cached = True
            if meta_path.exists():
                segment.request_id = json.loads(meta_path.read_text()).get("request_id")
        else:
            preview = segment.text[:58] + ("..." if len(segment.text) > 58 else "")
            print(f"  [{position + 1}/{len(speech)}] {preview}")
            data, request_id = tts(session, segment.text, prev_text, next_text,
                                   stitch_ids, args.voice, args.model,
                                   DEFAULT_VOICE_SETTINGS, args.output_format,
                                   api_key)
            audio_path.write_bytes(data)
            meta_path.write_text(json.dumps(
                {"request_id": request_id, "text": segment.text}, indent=2))
            segment.request_id = request_id

        if segment.request_id:
            stitch_ids.append(segment.request_id)
            stitch_ids = stitch_ids[-MAX_STITCH_IDS:]

        clip = trim_silence(AudioSegment.from_file(audio_path))
        segment.rendered_ms = len(clip)
        audio_by_index[segment.index] = clip

    track = AudioSegment.empty()
    for segment in script.segments:
        if segment.kind == "pause":
            track += AudioSegment.silent(duration=int(segment.seconds * 1000),
                                         frame_rate=44100)
        else:
            track += audio_by_index[segment.index]

    out = Path(args.out)
    track.export(out, format=out.suffix.lstrip(".") or "wav")
    write_report(script, Path(args.report))

    fresh = sum(1 for s in speech if not s.cached)
    print(f"\nWrote {out} — {fmt(len(track) / 1000)}")
    print(f"{fresh} line(s) generated, {len(speech) - fresh} served from cache")
    print(f"Timing report: {args.report}")


def write_report(script: Script, path: Path) -> None:
    cursor = 0.0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["start", "kind", "movement", "seconds", "text"])
        for segment in script.segments:
            seconds = (segment.seconds if segment.kind == "pause"
                       else segment.rendered_ms / 1000)
            writer.writerow([fmt(cursor), segment.kind, segment.movement,
                             f"{seconds:.2f}", segment.text])
            cursor += seconds


def fmt(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def dry_run(script: Script, wpm: float) -> None:
    print(f"Parsed {len(script.segments)} segments "
          f"({len(script.speech)} spoken, "
          f"{len(script.segments) - len(script.speech)} pauses)\n")

    order: list[str] = []
    speech_s: dict[str, float] = {}
    pause_s: dict[str, float] = {}

    for segment in script.segments:
        if segment.movement not in order:
            order.append(segment.movement)
            speech_s[segment.movement] = 0.0
            pause_s[segment.movement] = 0.0
        if segment.kind == "pause":
            pause_s[segment.movement] += segment.seconds
        else:
            speech_s[segment.movement] += len(segment.text.split()) / wpm * 60

    print(f"{'Movement':<38}{'Speech':>10}{'Silence':>10}{'Ends':>10}")
    cursor = 0.0
    for movement in order:
        cursor += speech_s[movement] + pause_s[movement]
        print(f"{movement[:37]:<38}{fmt(speech_s[movement]):>10}"
              f"{fmt(pause_s[movement]):>10}{fmt(cursor):>10}")

    speech_total = sum(speech_s.values())
    pause_total = sum(pause_s.values())
    print(f"\n{'TOTAL':<38}{fmt(speech_total):>10}{fmt(pause_total):>10}"
          f"{fmt(cursor):>10}")
    print(f"\nSilence is {pause_total / cursor * 100:.0f}% of the narration.")
    print(f"Billable characters: {script.characters:,} "
          f"(~{script.characters / 1000 * 0.03:.2f} credits-equivalent lines)")
    print(f"Projected voice-out at {fmt(cursor)} "
          f"(spec target 0:27:40, at {wpm:.0f} wpm)")


def main() -> int:
    # Before the parser is built: --voice defaults off ELEVENLABS_VOICE_ID.
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("script", nargs="?", default="script_a.txt")
    parser.add_argument("--out", default="narration.wav")
    parser.add_argument("--report", default="timings.csv")
    parser.add_argument("--cache", default=".tts-cache")
    parser.add_argument("--voice", default=os.environ.get("ELEVENLABS_VOICE_ID", ""),
                        help="voice id, or a voice name to look up")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--movement", type=int,
                        help="render only this movement, 1-based, for auditioning")
    parser.add_argument("--wpm", type=float, default=DEFAULT_WPM,
                        help="pace assumption for --dry-run only")
    parser.add_argument("--dry-run", action="store_true",
                        help="parse and project timing without calling the API")
    parser.add_argument("--list-voices", action="store_true",
                        help="print the account's voices and their ids, then exit")
    args = parser.parse_args()

    if args.list_voices:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            print(MISSING_KEY, file=sys.stderr)
            return 1
        print_voices(fetch_voices(api_key))
        return 0

    path = Path(args.script)
    if not path.exists():
        print(f"No such script: {path}", file=sys.stderr)
        return 1

    script = parse_script(path)

    if args.movement:
        movements = []
        for segment in script.segments:
            if segment.movement not in movements:
                movements.append(segment.movement)
        if args.movement > len(movements):
            print(f"Script has {len(movements)} movements", file=sys.stderr)
            return 1
        wanted = movements[args.movement - 1]
        script = Script([s for s in script.segments if s.movement == wanted])
        print(f"Movement {args.movement}: {wanted}\n")

    if args.dry_run:
        dry_run(script, args.wpm)
        return 0

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print(MISSING_KEY, file=sys.stderr)
        return 1
    if not args.voice:
        print(MISSING_VOICE, file=sys.stderr)
        return 1

    args.voice = resolve_voice(args.voice, api_key)

    render(script, args, api_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
