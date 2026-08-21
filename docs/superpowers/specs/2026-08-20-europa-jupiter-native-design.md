# Europa Jupiter Native Video

## Goal

Replace Europa's generated Jupiter slot with the native 30 fps Juno video and
remove the obsolete 14-frame dissolve/held-still transition. The slot remains
195 frames (6.5 seconds), so every later Europa timestamp stays unchanged.

## Design

`stories/07-europa-plates.json` will add the project-local
`nimbatus-review/jupiter/cand/PIA22906_nasa.mp4` input and split the current
intro segment around the Jupiter slot:

1. Intro frames `0..497`
2. Native Juno video, `0..6.5` seconds
3. Intro frames `692..1725`

The concat order and all other Europa segments remain unchanged. No blend,
fade, still, grade, crop, or `jupiter_styled.mp4` input will be used for the
Jupiter segment; the builder only performs the format/timestamp alignment
needed by the existing concat graph.

## Verification

- The Europa tests pin the three-part slot and reject the old styled input.
- The generated manifest and skill catalog remain fresh.
- Act VII is rendered with the native slot, and its duration remains 95.4 s.
- A review frame at the Jupiter slot shows native motion with no transition
  handoff or re-lighting.
- The megacut is not rebuilt.
