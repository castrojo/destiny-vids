# Lakshmi 01 Stage 1 authorized audio report

**Status: CORRECTED — v1 rejected for timing only; sample-exact v2 lossless
bed built in Argo. No picture or mux work performed.**

## Authorization and provenance

- Authorization reference: `User supplied local source: ~/Music/Ghost Love Score [aXYzFIdXeG8].webm on 2026-08-26`.
- Source endpoint: `http://192.168.1.227:8877/.work-lakshmi01/authorized-ghost-love-score.webm`.
- Expected and Argo-fetch-verified SHA-256:
  `ec29bdc72b6a1c1b9cc09f6da1930b59cbd240bedfe67dfb6e46050397fe9b74`.
- Receiver: `http://192.168.1.227:8880`, writing to `.work-lakshmi01`.
- Argo identity record: 63,464,591-byte Matroska/WebM; 602.101000 seconds;
  VP9 video and one Opus `48000` Hz stereo `fltp` stream.

All media/container work occurred in Argo. Local handling was limited to
opaque-byte hashing and reading returned text/JSON/PNG records.

## Workflows and trim

| Run | Workflow / UID | Parameters | Result |
| --- | --- | --- | --- |
| Analysis candidate | `lakshmi01-bed-876l7` / `d6ee7fb1-ca58-483d-8fab-1e96df4c1a09` | prefix `lakshmi01-ghost-love-score-analysis-602s-v1`, `-ss 0`, `-t 602` | Succeeded, 23:00:03–23:01:08 -04:00 |
| V1 final bed | `lakshmi01-bed-lwfvw` / `66abe67f-b410-45cd-9860-43da81d18b0e` | prefix `lakshmi01-ghost-love-score-bed-v1`, input `-ss 0 -t 595.040917` | Rejected for timing only: 28,560,956 samples / 595.019916667 s |
| V2 final bed | `lakshmi01-bed-v2-h4h2t` / `76571918-9e60-4ae5-86e3-0c59a09a3d97` | prefix `lakshmi01-ghost-love-score-bed-v2`, `atrim=start_sample=0:end_sample=28561964` | Succeeded, 23:16:33–23:17:41 -04:00 |

Remote `silencedetect=noise=-50dB:d=0.5` found no qualifying leading silence
and one trailing interval: `595.040917..602.08` (7.039083 seconds). V1's
input-side seek lost `1,008` valid samples to Opus packet granularity, so its
bed SHA-256 is rejected only as a timing input; all v1 evidence remains
retained. V2 decodes first and retains exactly samples `0..28,561,963`
(exclusive `end_sample=28561964`) with `atrim` and `asetpts`. Its exact
duration is **595.040916667 seconds** and drives
`round(595.040916667 * 24) = 14,281` picture frames (the 24-fps timeline is
595.041666667 seconds).

## Gates and measurements

| Gate / measurement | Result |
| --- | --- |
| Source hash | Pass; expected equals fetched value |
| Native rate | Pass; exactly 48,000 Hz |
| V2 PCM handoff | Pass; `pcm_s24le`, 48,000 Hz stereo |
| V2 format/sample gate | Pass; `time_base=1/48000`, `duration_ts=28561964` |
| >16 kHz RMS | -44.442325 dB |
| 8 kHz one-octave RMS | -26.216792 dB |
| Spectral ratio | -18.23 dB, pass (above -46 dB; no review warning) |
| V2 returned audio gate | `overall: pass`; format/sample sub-gate pass |
| V2 remote PCM loudness | -8.0 LUFS integrated; 9.4 LU LRA |
| V2 remote PCM true peak | +0.5 dBFS |

The timing-rejected v1 bed remains at
`.work-lakshmi01/lakshmi01-ghost-love-score-bed-v1-bed.wav`, SHA-256
`f55d994002b2f56aaab3d21c38ea12473a48a3a8cfe33db2dcb235ed0799c8be`.
The accepted final bed is
`.work-lakshmi01/lakshmi01-ghost-love-score-bed-v2-bed.wav`, SHA-256
`06488412372e2e310a89e2e862c6e7dc5f5e37a02767ebb5eb0009d524de15c3`.
Its remote `bed-format-gate.json` and `audio-gate.json` both pass (SHA-256
`d896b3e8e75fcc28f4d7b88b6959a29ab97d916801fef788f122eae8e3b57e0c` and
`f47d07df8071a315ca26072429f79789c5f21e718578985da278305ea052b146`).
Returned source, format, silence, spectrum, metric, bed-build, ebur128, gate,
workflow-status, and `SHA256SUMS` artifacts are retained in the work directory
under both prefixes; their complete hash inventory is in
`.work-lakshmi01/verify-notes.md`.

## Concern and next boundary

Stage 1 passes, but the PCM ebur128 true peak is +0.5 dBFS. Before a delivery,
Stage 2 must test one or more **static-gain-only** AAC candidates from this
original verified PCM bed and accept only a decoded candidate below -0.1 dBTP
(target -0.9 to -1.1 dBTP). Do not normalize, compress, limit, EQ, resample,
or use an earlier AAC candidate as input. The provisional silent picture
remains untouched and must be retimed from this measured bed only in a future
authorized picture workflow.
