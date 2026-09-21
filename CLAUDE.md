# The 3AM Sessions

A faceless YouTube channel of 3-hour sleep meditations, aimed at the
middle-of-the-night waking moment rather than bedtime. Modelled on the
structure of the Chibs Okereke Sleep Meditations channel, not its content.

Owner: Ben Moore. Episode 1 is in production; nothing has been published yet.

## The format

3-hour video. Original narration runs the first 23:52 over a rain bed; the
rain then carries the remaining ~2.5 hours, tapering slowly so nothing wakes
the listener. Still frame, never a moving loop. Nothing — no chime, no outro,
no end screen — after the voice stops.

The script's premise is *permission*: the core problem at 3am is not the
waking, it's the second-order panic about being awake. Movement 2 explicitly
removes the requirement to fall asleep. Keep that. It is the channel's
differentiator and the reason the voice casting works.

## Status

| Piece | State |
| --- | --- |
| Ep.1 script | Done, `script_a.txt`, 785 words / 4,119 billable chars |
| Render pipeline | Done and verified, `render.py` |
| Assembly pipeline | Done and verified, `assemble.py` |
| Still frame | Done, `art/rain_window_1080_graded.png` |
| Voice | Chosen — an elderly Scottish grandfather voice on ElevenLabs |
| Narration audio | **Not yet rendered.** Next step. |
| Rain bed | **BLOCKED — this is the open problem.** See below. |
| Script B | Not written |

## The open problem: the rain bed

We need 10–15 minutes of steady rain, licensed for commercial use, to feed
`assemble.py`. Two approaches have been tried and rejected:

1. **AI-generated video clips (Veo, MiniMax via Viewmax).** Clips are 8–15s.
   Even with a perfect crossfade the *content* repeats 700–1,300 times over
   three hours, which a sleepless listener will find. Measured level swings of
   11–20 dB on top of that. One clip had no audio stream at all.
2. **Spectral synthesis** (`make_bed.py`). Matches a reference clip's
   long-term average spectrum onto endlessly fresh noise. Measured beautifully
   — 0.7 dB level spread, spectrum within 2.6 points of the reference on every
   band, no periodicity against a looped control. **Ben listened and said both
   variants sound synthetic, nothing like rain.** Matching the average
   spectrum is necessary but not sufficient; rain's character lives in dense
   droplet microstructure that shaped noise does not reproduce.

**Do not re-propose either approach.** The remaining path is a real
recording: licensed from a sound library, or recorded by Ben (he is in
Rhode Island; a phone on a windowsill in a storm is free and unambiguously
his). Verify any candidate with `python assemble.py FILE --analyze-only`
before buying or committing to it.

`make_bed.py` is kept only as a record of what was tried. It is not part of
the working pipeline.

## Files

- `script_a.txt` — Ep.1 narration. `[P n]` = n seconds of silence, alone on
  its own line. `##` headings are movements. `#` lines are comments.
- `render.py` — script → `narration.wav` via the ElevenLabs API.
- `assemble.py` — rain + narration + still → 3-hour `master.mp4`.
- `make_bed.py` — rejected, see above.
- `art/` — the still frame, graded and ungraded 1920×1080.

## Commands

```bash
cp .env.example .env                  # then fill in key and voice id
pip install requests pydub numpy      # ffmpeg must be on PATH

python render.py --dry-run                        # free, proves timing
python render.py --list-voices                    # free, names -> voice ids
python render.py --check                          # free, gates the render
python render.py --movement 1 --out audition.wav  # 493 chars
python render.py --out narration.wav              # 4,119 chars

python assemble.py rain.wav --analyze-only        # vet a rain source
python assemble.py rain.wav --narration narration.wav --still art/rain_window_1080_graded.png
```

Credentials live in `.env` beside `render.py`, which is gitignored; a shell
export still overrides it. The key never goes in the repo, in a commit, or in
a chat transcript — if one leaks, rotate it in the ElevenLabs dashboard.
`--voice` takes a voice name as well as an id, so `--voice Angus` works once
`--list-voices` has told you the name.

## Hard-won details — do not rediscover these

- **Pauses are never sent to the TTS.** No model reliably produces a 60-second
  silence; asked for one it invents breath or clips the tail. `render.py`
  sends speech only, trims each clip's own head and tail, and builds every gap
  locally. This is also why the script is cheap: you are billed for ~9.5
  minutes of speech, not 24 minutes of runtime.
- **The loop crossfade must be equal-power (cos/sin), not linear.** Rain is
  uncorrelated with itself, so linearly-faded copies sum in power and the
  overlap loses 3 dB at its midpoint — an audible lull every repetition. This
  is fixed in `assemble.py`; do not "simplify" it back.
- **Encode at 1 fps with a 5-minute GOP.** The frame never changes, so nearly
  all bitrate goes to keyframes. Measured: 478 MB → 96 MB for 3 hours of
  video. B-frames help; `-bf 0` nearly doubled it again.
- **ffmpeg's `volumedetect` writes at info level.** `-v error` silently
  swallows its output. Cost an hour once.
- **`--check` gates the render.** It reads the subscription endpoint and
  refuses on a non-commercial tier, on a quota that will not cover the
  script, or on a voice id that does not resolve. All free. Run it before
  every paid render; the four things it checks are the four that have gone
  wrong, and all of them are invisible until after the credits are spent.
- **ElevenLabs free tier carries no commercial licence at all.** Starter
  (~$6/mo, 30k credits) covers the entire six-upload first series with room to
  spare. Creator's extras (192 kbps, professional voice cloning) do not apply
  here. Confirm the chosen tier can mint an API key before paying — the
  pricing page lists a separate API tier and the docs do not clarify.
- **Timings in the spec were corrected to measured values.** Voice-out is
  0:23:52, not the 27:40 originally estimated. `assemble.py`'s `TAPER` keys
  off `VOICE_OUT`, so re-pacing the script moves the whole curve with it.
- **The still frame is a still, deliberately.** A moving loop is visible
  through closed eyelids on a nightstand phone, encodes far larger, and
  signals "something to watch" rather than "audio product".

## Series plan

Six uploads from two scripts: Script A on rain / pink noise / voice-only,
Script B (racing thoughts, not yet written) on rain / distant thunder / pink
noise. Re-render the same voice take against each bed rather than
re-recording. Publish 1, 4 and 2 weekly, then hold for four weeks of data.

Keep the two scripts genuinely distinct rather than templating one with
swapped nouns — that pattern is what YouTube's inauthentic-content
enforcement looks for, and it is the main monetization risk on this channel.
