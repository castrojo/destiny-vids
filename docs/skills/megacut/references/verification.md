# Verify, don't assert

Reference for [`../SKILL.md`](../SKILL.md). A programme that "wrote" is not yet
proved; these are the manual probes that caught real defects.

A log that says `wrote …` proves nothing. Every one of these has caught a real
defect:

```bash
ffmpeg -v error -xerror -i out.mp4 -f null -        # not truncated
ffprobe -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space
ffmpeg -ss <seg> -t <len> -i out.mp4 -map a:0 -af volumedetect -f null /dev/null
```

- **Duration equals the sum of the parts.** Not approximately: an 8.5 s
  shortfall on a 20-minute programme is one act silently truncated, and the
  file plays fine. **`assemble()` enforces this itself** — each segment's
  video extent against its source, and the programme against the plan's sum —
  so a re-time fails the build instead of shipping (#88). The manual checks
  below are for what a duration cannot see.
- **Every act slide lands where the plan says.** Cheap and decisive: extract a
  frame per second (`-vf fps=1,scale=64:36`), compare each against the rendered
  `plate_act*.png`, and print where each slide actually starts. A slide that is
  early is the act before it having been truncated.
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Silent stretches read at the noise floor** (about −91 dB for AAC digital
  silence), not merely "quiet".
- Extract frames either side of every join **and look at them**.
