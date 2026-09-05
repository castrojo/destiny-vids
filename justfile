# Season of the Blueberries: episode and season builds.
# The whole interface is tools/hive_series.py; these recipes are one line
# over its CLI. The Hive workspace runs farm ONLY (tools/farm.py): no local
# ffmpeg/ffprobe at all -- preflight, encode, join, and validation are the
# farm's, and an unreachable cluster fails the build visibly. Builds write
# the reviewable roughs (rough/s01eNN-*.mp4, season-01-full-rough.mp4);
# finals change only through `promote`/`promote-cut` after local approval.

# Build and verify one episode's rough.
hive-episode NUMBER:
    python3 tools/hive_series.py build {{NUMBER}}

# Build and verify all twelve episode roughs, then assemble the rough cut.
hive-cut:
    python3 tools/hive_series.py cut

# Regenerate the committed cards (opening CTA + the twelve title slides).
hive-cards:
    python3 tools/hive_series.py cards
