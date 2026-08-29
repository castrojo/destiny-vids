# Season of the Blueberries: episode and season builds.
# The whole interface is tools/hive_series.py; these recipes are one line
# over its CLI. Encoding is farm-first (tools/farm.py); --local is the
# memory-capped escape hatch: `just hive-episode 3 -- --local` is NOT wired
# up -- pass the flag directly: `python3 tools/hive_series.py build 3 --local`.

# Build and verify one episode.
hive-episode NUMBER:
    python3 tools/hive_series.py build {{NUMBER}}

# Build and verify all twelve episodes, then concatenate the full-season cut.
hive-cut:
    python3 tools/hive_series.py cut

# Regenerate the committed cards (opening CTA + the twelve title slides).
hive-cards:
    python3 tools/hive_series.py cards
