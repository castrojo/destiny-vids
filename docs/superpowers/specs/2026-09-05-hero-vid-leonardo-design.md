# Hero Video: Leonardo — Ten Thousand Against One

## Goal

Create a hero character music video for **Leonardo** set to Unleash The Archers' "Ten Thousand Against One". The production melds the band's official lyric video with Leonardo's artwork, displaying the filled-in character drawing permanently on a clear canvas as the hero visual, while the band's video plays in a dedicated smaller frame styled in the Project Bluefin video design language.

## Inputs & Provenance

### Character Artwork
- **Primary Hero Still**: `/var/home/jorge/Downloads/leonardo/CHA_LEONARDO_01.png` (3720x3173 RGBA, transparent background, alpha bbox `41, 212, 3543, 3143`).
- **Additional Staged Assets**:
  - `CHA_LEONARDO_01.mp4` (drawing process animation)
  - `CHA_LEONARDO_03.png`, `CHA_LEONARDO_04.png` (alternate character stills)
  - `CHA_LEONARDO_WEAPONS.png` (weapons sheet)
  - `Cha Design_LEONARDO.jpg` (concept design sheet)

### Music & Video Source
- **File**: `~/Music/UNLEASH THE ARCHERS - Ten Thousand Against One (Official Lyric Video) ｜ Napalm Records [sMMboHJJFPI].webm`
- **Origin**: Napalm Records / Unleash The Archers official lyric video (`sMMboHJJFPI`).
- **Usage Class**: `third_party_copyrighted` (non-commercial fan creation under fair dealing/fan-edit convention).
- **Audio Treatment**: Complete native track decoded directly on the Argo cluster at 48 kHz stereo; measured gain without normalization.

## Visual Design & Composition (Bluefin Video Design Language)

### Frame Specification
- **Resolution**: 2560x1440 (16:9 QHD master).
- **Frame Rate**: 24.0 fps constant frame rate (`fps=24`).
- **Codec**: H.264 high profile, CRF 17, `yuv420p`, `+faststart`.
- **Audio**: AAC 320 kbps, 48 kHz stereo.

### Canvas & Layout Structure
- **Canvas Background**:
  - Clean atmospheric canvas matching the Bluefin palette: deep navy/slate foundation (`#0c1017` to `#161f2e`) layered with subtle day-to-night crossfade texture across the duration.
  - Zero black pillarboxes or untextured margins.
- **Hero Character (Leonardo)**:
  - `CHA_LEONARDO_01.png` rendered permanently on the clear canvas as the main subject throughout the entire video.
  - Sized to 85% of frame height (`scale=-2:1224`), seated in the right two-thirds of the canvas with boots comfortably above the lower margin and head below the upper edge.
- **Band Video Panel (Smaller Inset)**:
  - Band lyric video scaled to 1024x576 (16:9) and positioned in the left third / center-left of the frame.
  - Framed in an angular Bluefin HUD container:
    - 2px `#4285f4` border rule.
    - Chamfered/angled HUD corners.
    - Translucent glass backing (`rgba(12, 16, 23, 0.82)`) with a subtle drop shadow to cleanly separate the lyric feed from the underlying canvas.
  - Ensures band lyrics remain sharp and legible while letting Leonardo own the broader visual stage.

### Corner Furniture
- **Bottom-Left**:
  - Text wordmark: `wolves.projectbluefin.io`.
  - Styling: Pure white glyphs, with dots rendered in `#4285f4`. Text only, never a QR code.
- **Bottom-Right**:
  - Support QR card for Unleash The Archers.
  - Styling: `slate` style (engraved, dark chrome matching the film's UI system), 280px wide, seated 48px from the bottom and right edges.
  - Resolves to `https://www.unleashthearchers.com/`.

## Architecture & Pipeline

### Remote Cluster Rule (Argo Farm Only)
Per repository policy and owner ruling: **zero local ffmpeg or ffprobe execution**. Probing, audio measurement, decoding, compositing, and verification runs exclusively as Argo workflows in the `argo` namespace on the local cluster (`192.168.1.170`). Local operations are strictly limited to Python metadata generation, Pillow/OpenCV inspection of exported PNGs, and JSON/YAML manifest generation.

### Stage Breakdown

1. **Preflight & Audio Bed (Stage 1)**:
   - Submit Argo workflow to probe source container geometry, timebase, exact sample count, and native audio format.
   - Extract bit-perfect PCM WAV bed (`pcm_s24le`, 48 kHz stereo) to the workstation receiver (`upload-server.py`).
   - Derive authoritative target duration `T` and exact frame count `target_frames = round(T * 24)`.

2. **Overlay & Frame Generation**:
   - Author `scripts/build_leonardo_hero_overlay.py` in `castrojo/destiny-vids`.
   - Render static 2560x1440 RGBA overlay carrying the HUD frame for the band video, corner wordmark, and QR card.
   - Validate overlay with offline pytest tests (`tests/test_leonardo_hero_overlay.py`).

3. **Remote Video Composite (Stage 2)**:
   - Remote Argo encode pod mounts source files over HTTP (`python3 -m http.server 8877`).
   - Filtergraph:
     - Scales and positions Leonardo PNG over background canvas.
     - Scales band video to 1024x576, lays it over the HUD panel window.
     - Composites full-frame overlay (`overlay=0:0`).
     - Applies `setpts` retiming to lock video to `target_frames` at 24 fps.
   - Uploads intermediate picture stream and probe logs to workstation.

4. **Mux & Verification (Stage 3)**:
   - Combine picture with native audio bed using single static gain.
   - In-pod verification:
     - Clean decode check (`ffmpeg -v error -i ... -f null -`).
     - Stream probe confirming 2560x1440, 24 fps, no audio sync drift.
     - Extract sample frames (including day and night states) to verify QR decodability and layout integrity.
   - Save all measurements and run logs in `~/Videos/Wolves/Hero/.work-leonardo01/verify-notes.md`.

5. **Deliverable Promotion**:
   - Promote deliverable to root: hardlink `.work-leonardo01/LEONARDO_01-music-video.mp4` to `~/Videos/Wolves/Hero/LEONARDO_01-music-video.mp4`.
   - Build 1920x1080 thumbnail under 2 MB from `CHA_LEONARDO_01.png` using canonical Bluefin HUD nameplate in `tools/plate.py`.

## Verification & Acceptance Criteria

- [ ] Spec approved by user before execution.
- [ ] No local `ffmpeg` or `ffprobe` commands executed.
- [ ] Complete song audio preserved at native 48 kHz stereo.
- [ ] Leonardo's filled-in drawing remains visible on the clear canvas for the entire video duration.
- [ ] Band lyric video is framed cleanly in a smaller Bluefin HUD container without obscuring the artwork.
- [ ] Corner furniture strictly adheres to Bluefin guidelines (bottom-left URL text, bottom-right QR card).
- [ ] Final video promoted to `~/Videos/Wolves/Hero/LEONARDO_01-music-video.mp4` and verified cleanly.
