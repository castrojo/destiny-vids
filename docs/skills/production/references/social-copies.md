# Social copies

Part of the [production skill](../SKILL.md).

## A social copy is a delivery stage

```bash
python3 tools/social.py ~/Videos/Wolves/Prod/<act>.mp4 \
    --out ~/Videos/Wolves/10mb/<act>.mp4 --audio-bitrate 256
```

Social platforms cap an upload by **bytes**, so `tools/social.py` solves for the
video bitrate from the duration and the audio budget and spends exactly that in
a two-pass encode — the file lands under the cap by arithmetic, not by re-rolling
a CRF until one happens to fit. `--dry-run` prints the budget first.

Two rules, and the second is the one that gets broken:

- **Encode from `Prod/`, never from another social copy.** A copy of a copy is
  two lossy generations for no reason.
- **Re-encoding is allowed; processing is not.** No normaliser, no limiter, no
  EQ — the peak of a social copy must match its master's, and a test asserts the
  tool contains no filter that would change it. A starved music bed is the
  artifact people actually hear on a phone, so spend bitrate on audio first.

