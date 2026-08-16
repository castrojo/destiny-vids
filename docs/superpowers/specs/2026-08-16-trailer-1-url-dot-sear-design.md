# Trailer 1 URL dot sear

## Decision

The two dots in Trailer 1's `wolves.projectbluefin.io` CTA become compact blue
sears. The URL’s `b` and `f` remain white exactly as the owner requested.

## Treatment

The CTA dots receive a 1 px near-white core with a small Bluefin-blue falloff:
the existing sear palette's flare, mid, and halo values are reused. The spread
is intentionally smaller than the event headline's vertical seared pipe, so
two tiny punctuation marks read as sparks rather than competing light sources.

The treatment is scoped to `.poster-cta .accent`. It does not alter ordinary
Bluefin letters, the event headline’s pipe, the prologue, or the URL’s white
letters.

## Verification

The card-template test pins the poster-dot selector and its use of the
existing `SEAR_FLARE`, `SEAR_MID`, and `SEAR_HALO` values. Render Trailer 1,
inspect the end-card frame, and run the full repository gates.
