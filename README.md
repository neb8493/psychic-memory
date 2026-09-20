# The 3AM Sessions

Production repo for a faceless YouTube channel of 3-hour sleep meditations,
aimed at the middle-of-the-night waking moment rather than bedtime.

The script, the render and assembly pipelines, and the still frame are here.
Rendered audio and finished masters are not — they are regenerated from
`script_a.txt` and a rain source.

See [CLAUDE.md](CLAUDE.md) for the format, current status, the open problem
(the rain bed), and the hard-won pipeline details that should not be
rediscovered.

## Quick start

```bash
export ELEVENLABS_API_KEY='...'      # shell profile, never the repo
export ELEVENLABS_VOICE_ID='...'
pip install requests pydub numpy      # ffmpeg must be on PATH

python render.py --dry-run            # free, proves timing
```
