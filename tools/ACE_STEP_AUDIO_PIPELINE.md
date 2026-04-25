# ACE-Step Audio Pipeline

Goal: produce final production audio assets for Warpath Reels while keeping the frontend aligned with StakeEngine's event-driven frontend pattern.

## Principle

Do not run AI music generation in the frontend. Generate and master audio offline, commit static audio assets, and play them through `frontend/static/assets/audio/manifest.json`.

## Production Steps

1. Generate candidate tracks with ACE-Step using the prompts in `frontend/static/assets/audio/README.md`.
2. Export each final stem as WAV at 44.1 kHz stereo.
3. Trim loops to exact bar boundaries and validate seamless looping.
4. Normalize and master:
   - Background loops: around `-18 LUFS` integrated, peaks below `-2 dBTP`.
   - SFX/stingers: peaks below `-1 dBTP`; avoid masking the win counter and UI.
5. Replace the existing WAV files in `frontend/static/assets/audio/` without changing filenames.
6. Update `manifest.json` volumes only if mastering levels require it.
7. Run:

```bash
pnpm build
```

8. Test events through real gameplay books:
   - `reelsSpin`
   - `cascadeExplode`
   - `wildPulse`
   - `globalMultiplier`
   - `featureIntro`
   - `winCounter`
   - `finalWin`

## StakeEngine Alignment

StakeEngine frontend docs describe the frontend flow as ordered bookEvents processed by `playBookEvents()`, then routed through `bookEventHandlerMap` into typed emitterEvents and component subscribers. Audio follows the same path in `WarpathAudio.svelte`.

## License Gate

Before final upload, record:

- Model name and version.
- License URL.
- Prompt text.
- Seed/settings if available.
- Date generated.
- Any post-processing/mastering chain.

Do not ship audio generated with non-commercial model weights.
