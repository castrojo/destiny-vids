"""Tests for scripts/make_video.sh, the issue-to-render pipeline spine.

The script is the only thing in the repo that runs every stage in order, and
it carries the stage-7 `clean` gate: the check that refuses to render a whole
video, credited under real people's names, while an unclean beat would survive
into the finished file. These tests run the real script as a subprocess
against a scratch tree in tmp_path:

- scripts/make_video.sh is COPIED from the repo, so the thing under test is
  the thing that ships. tools/, vocab/ and schema/ are copied too -- the gate
  resolves redactions/ relative to tools/redact.py's real location, which
  copying (not symlinking) keeps inside the scratch tree. The repo's real
  segments/, tags/, media/ and redactions/ are never touched.
- scripts/build_uncut_credited.sh is the one deliberate stub: reaching it is
  the assertion for a passing gate, and the real one renders footage, which
  the suite never touches. The stub records its arguments instead.
- gh, yt-dlp and ffprobe are PATH stubs: the suite is offline, and a stub
  that fails loudly is how a test proves it can never escape to the network.
  The one online tool the script calls directly is tools/ingest.py (a YouTube
  oEmbed lookup), so the python3 PATH shim answers that call with the tool's
  own offline switch, --title. Every other python3 call passes through.
- media/<id>.mp4 is an empty placeholder for tests that stop before stage 6.
  Tests that run stage 6 need real detection, because assemble re-detects
  beats from the media: they write a tiny cv2 clip and derive the beats
  manifest from whatever the real detector says about it. Those tests skip
  when scenedetect + opencv (optional extras, AGENTS.md) are absent.
"""
import importlib.util
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.ingest import slug  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "make_video.sh"
REAL_PYTHON = sys.executable

# Stage 6 (assemble) runs tools/annotate.py index, which refuses to run without
# scenedetect and detects nothing without a decodable clip. The stages up to 5
# only check that files exist, so their tests run everywhere.
HAVE_FRAME_TOOLS = all(
    importlib.util.find_spec(module) is not None
    for module in ("scenedetect", "cv2")
)
needs_frame_tools = pytest.mark.skipif(
    not HAVE_FRAME_TOOLS,
    reason="stage 6 runs real shot detection: scenedetect + opencv are "
           "optional extras (AGENTS.md); without them annotate.py index exits 2",
)

VIDEO_ID = "yt_destiny_2_test_cinematic"
WATCH_URL = "https://www.youtube.com/watch?v=TESTVIDEO01"

# The title the python3 shim hands to tools/ingest.py --title. The video_id a
# URL-only brief resolves to is derived from it, exactly as ingest derives it.
SHIM_TITLE = "Destiny 2: Test Cinematic (make_video.sh tests)"
INGESTED_ID = f"yt_{slug(SHIM_TITLE)[:60]}"

BLOCKED_ON = "Owner must confirm the plate copy before anything renders."


# ---------------------------------------------------------------------------
# the scratch tree
# ---------------------------------------------------------------------------

class PipeTree:
    """A throwaway copy of the repo layout that make_video.sh runs against.

    The script cd's to REPO_ROOT computed from its own location, so copying it
    to <root>/scripts/ makes <root> the repo it operates on.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.bin = self.root / "bin"
        for sub in ("scripts", "tools", "vocab", "schema", "videos", "media",
                    "keyframes", "tags", "segments", "redactions", "bin"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy(SCRIPT, self.root / "scripts" / "make_video.sh")
        for path in (REPO_ROOT / "tools").glob("*.py"):
            shutil.copy(path, self.root / "tools" / path.name)
        for path in (REPO_ROOT / "vocab").glob("*.yaml"):
            shutil.copy(path, self.root / "vocab" / path.name)
        for path in (REPO_ROOT / "schema").glob("*.json"):
            shutil.copy(path, self.root / "schema" / path.name)
        self._write_shims()
        self.issue_body = self.root / ".issue_body.txt"
        self.issue_body.write_text("no brief\n", encoding="utf-8")

    # -- PATH doubles --------------------------------------------------------

    def _write_shims(self):
        # The credited build renders real footage. The unit under test here is
        # make_video.sh's orchestration, so the boundary is the hand-off: the
        # stub records its arguments, and reaching it at all is the assertion.
        self._exe("scripts/build_uncut_credited.sh", """#!/usr/bin/env bash
echo "stub build_uncut_credited: $*"
printf '%s\\n' "$*" >> build_calls.txt
""")
        # Reaching yt-dlp in a test is a fixture bug, not a network request.
        self._exe("bin/yt-dlp", """#!/usr/bin/env bash
echo "yt-dlp stub: tests are offline; pre-create media/<id>.mp4" >&2
exit 1
""")
        # The codec check only warns; answering h264 keeps the suite off the
        # host's ffprobe entirely (on Bluefin it is a podman container shim).
        self._exe("bin/ffprobe", """#!/usr/bin/env bash
echo h264
""")
        # Only `python3 tools/ingest.py <url>` is intercepted: its one online
        # step is the oEmbed title lookup, and --title is the tool's own
        # offline switch. Every other python3 call passes through untouched.
        self._exe("bin/python3", f"""#!/usr/bin/env bash
if [ "${{1:-}}" = "tools/ingest.py" ]; then
    shift
    exec {shlex.quote(REAL_PYTHON)} tools/ingest.py "$@" \\
        --title {shlex.quote(SHIM_TITLE)}
fi
exec {shlex.quote(REAL_PYTHON)} "$@"
""")
        self._exe("bin/gh", f"""#!{REAL_PYTHON}
import json, os, sys
if len(sys.argv) >= 3 and sys.argv[1] == "issue" and sys.argv[2] == "view":
    with open(os.environ["FAKE_ISSUE_BODY"], encoding="utf-8") as fh:
        body = fh.read()
    print(json.dumps({{"number": int(sys.argv[3]),
                      "title": "Fake issue", "body": body}}))
    raise SystemExit(0)
print("gh stub: unhandled: " + " ".join(sys.argv[1:]), file=sys.stderr)
raise SystemExit(1)
""")

    def _exe(self, rel, text):
        path = self.root / rel
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # -- fixtures ------------------------------------------------------------

    def write_video_record(self, video_id=VIDEO_ID):
        from tools.ingest import build_video_record
        record = build_video_record(video_id, WATCH_URL, "Destiny 2: Test Cinematic")
        (self.root / "videos" / f"{video_id}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")

    def write_placeholder_media(self, video_id=VIDEO_ID):
        """Existence is all stages 3-5 check; stage 6 is never reached."""
        (self.root / "media" / f"{video_id}.mp4").touch()

    def write_manifest(self, beats, video_id=VIDEO_ID):
        """The beats.json pass 1 would have written alongside the keyframes."""
        keydir = self.root / "keyframes" / video_id
        keydir.mkdir(parents=True, exist_ok=True)
        manifest = [dict(b, beat_index=i, keyframe=f"{i:03d}.jpg")
                    for i, b in enumerate(beats)]
        (keydir / "beats.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest

    def write_clip_and_manifest(self, n_scenes=4, video_id=VIDEO_ID):
        """A tiny synthetic clip plus the manifest the REAL detector reports.

        Stage 6 re-detects beats from the media, so the manifest cannot be
        invented: it is whatever scenedetect says about this exact file. The
        scenes are one second of solid colour each -- a hard cut the content
        detector cannot miss.
        """
        import cv2
        import numpy as np

        media = self.root / "media" / f"{video_id}.mp4"
        writer = cv2.VideoWriter(str(media), cv2.VideoWriter_fourcc(*"mp4v"),
                                 10.0, (64, 64))
        assert writer.isOpened(), "cv2 could not open an mp4v writer"
        for shade in (0, 255, 90, 200)[:n_scenes]:
            frame = np.full((64, 64, 3), shade, dtype=np.uint8)
            for _ in range(10):
                writer.write(frame)
        writer.release()

        from tools import annotate
        beats = annotate.detect_beats(str(media), 0.0)
        assert len(beats) == n_scenes, f"detector saw {len(beats)} scenes"
        return self.write_manifest(beats, video_id)

    def write_tags(self, overlays, video_id=VIDEO_ID):
        """A FINISHED tag file, as the tagging stage would leave it: one entry
        per beat, keyed by beat index as a string, every tagger field filled
        (worksheet.py check stops the script at stage 5 while any field is
        absent or null). overlays is one list per beat -- the only field the
        tests vary, because it is the one the clean gate reads."""
        tags = {str(i): _full_tag(ov) for i, ov in enumerate(overlays)}
        (self.root / "tags" / f"{video_id}.json").write_text(
            json.dumps(tags, indent=2) + "\n", encoding="utf-8")

    def write_redactions(self, redactions, video_id=VIDEO_ID):
        (self.root / "redactions" / f"{video_id}.json").write_text(
            json.dumps({"video_id": video_id, "redactions": redactions},
                       indent=2) + "\n", encoding="utf-8")

    def write_issue(self, brief_yaml):
        self.issue_body.write_text(
            "A fake issue, filed the way owners file issues.\n\n"
            f"```brief\n{brief_yaml}```\n", encoding="utf-8")

    def write_roster(self):
        (self.root / "roster.json").write_text('{"leads": []}\n',
                                               encoding="utf-8")
        return "roster.json"

    # -- running -------------------------------------------------------------

    def run(self, *args):
        env = dict(os.environ)
        env["PATH"] = str(self.bin) + os.pathsep + env["PATH"]
        env["FAKE_ISSUE_BODY"] = str(self.issue_body)
        return subprocess.run(
            ["bash", "scripts/make_video.sh", *[str(a) for a in args]],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=240)

    def build_calls(self):
        """What the credited build was invoked with, or None if it never ran."""
        marker = self.root / "build_calls.txt"
        return marker.read_text().splitlines() if marker.exists() else None


@pytest.fixture
def pipe(tmp_path):
    return PipeTree(tmp_path)


def output(proc):
    return proc.stdout + proc.stderr


def _full_tag(overlays):
    """Every TAGGER_FIELD, filled the way the committed corpus fills them.

    An explicitly empty list is a positive judgement ("this frame is clean"),
    null is "nobody has looked" (tools/worksheet.py) -- so the tests say
    ``[]`` where they mean clean, and the shape mirrors
    tags/yt_curse_of_osiris_opening_cinematic.json.
    """
    return {
        "class": "unknown",
        "element": "unknown",
        "faction": [],
        "shot_scale": "INSERT",
        "composition": ["cutaway"],
        "camera_movement": ["static"],
        "pacing": "slow",
        "content_type": "cinematic",
        "lighting": "dim",
        "identity_visibility": "none",
        "character_identifiability": "unidentifiable",
        "substitutability": 0,
        "overlays": overlays,
        "subject_salience": "ambient",
        "action": [],
        "mood": ["ominous"],
        "register": 0,
        "character": [],
        "caption": "a synthetic test frame",
        "provenance": {},
    }


def seg_id(video_id, beat):
    """The segment_id assembly assigns a beat (tools/annotate.py)."""
    return (f"seg_{video_id}_{int(beat['start_sec']):04d}"
            f"-{int(beat['end_sec']):04d}")


def tail_cut_through(beat, video_end, acknowledges=None):
    """A tail redaction whose boundary runs through the middle of `beat`:
    the 'clean shot dissolving into a logo card' case the gate cannot resolve
    from geometry alone."""
    record = {"id": "tail_card",
              "start_sec": (float(beat["start_sec"]) + float(beat["end_sec"])) / 2,
              "end_sec": float(video_end),
              "reason": "logo card the last beat dissolves into",
              "action": "cut", "boxes": "full"}
    if acknowledges is not None:
        record["acknowledges"] = acknowledges
    return record


# ---------------------------------------------------------------------------
# 1. the stage-7 clean gate
# ---------------------------------------------------------------------------

@needs_frame_tools
def test_an_unclean_beat_surviving_redaction_whole_refuses_the_build(pipe):
    """The gate: an unclean beat inside the kept range would be rendered into
    the finished file under real people's names. The build must not run."""
    manifest = pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], ["hud"], [], []])       # beat 1 carries a HUD
    roster = pipe.write_roster()

    proc = pipe.run("--video-id", VIDEO_ID, roster)
    out = output(proc)

    assert proc.returncode == 1, out
    assert "REFUSING to build" in out
    hud_seg = seg_id(VIDEO_ID, manifest[1])
    assert hud_seg in out, "the refusal must name the offending segment"
    assert "overlays=['hud']" in out
    assert "4 segment(s), 3 clean" in out
    assert pipe.build_calls() is None


@needs_frame_tools
def test_a_straddled_beat_proceeds_when_the_redaction_acknowledges_it(pipe):
    """A redaction boundary cutting THROUGH an unclean beat is the one case
    the index cannot resolve: tags are beat-level, redaction is frame-level.
    The owner records the trust explicitly, per beat, in `acknowledges`."""
    manifest = pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], ["burned_text"]])
    pipe.write_redactions([
        tail_cut_through(manifest[3], manifest[3]["end_sec"],
                         acknowledges=[seg_id(VIDEO_ID, manifest[3])])])
    roster = pipe.write_roster()

    proc = pipe.run("--video-id", VIDEO_ID, roster)
    out = output(proc)

    assert "acknowledges it" in out
    assert "REFUSING" not in out
    assert proc.returncode == 0, out
    assert pipe.build_calls() == [f"{VIDEO_ID} {roster}"]


@needs_frame_tools
def test_the_same_straddled_beat_is_refused_without_the_acknowledgement(pipe):
    """The security property: identical geometry, no `acknowledges` entry.
    Trust must be explicit and owner-recorded -- a boundary that happens to
    overlap an unclean beat must never grandfather it in."""
    manifest = pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], ["burned_text"]])
    pipe.write_redactions([tail_cut_through(manifest[3], manifest[3]["end_sec"])])
    roster = pipe.write_roster()

    proc = pipe.run("--video-id", VIDEO_ID, roster)
    out = output(proc)

    assert proc.returncode == 1, out
    assert "REFUSING to build" in out
    assert seg_id(VIDEO_ID, manifest[3]) in out
    assert pipe.build_calls() is None


@needs_frame_tools
def test_a_fully_clean_video_passes_the_gate_to_the_build(pipe):
    manifest = pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], []])
    roster = pipe.write_roster()

    proc = pipe.run("--video-id", VIDEO_ID, roster)
    out = output(proc)

    assert proc.returncode == 0, out
    assert "4 segment(s), 4 clean" in out
    assert "==> build the credited cut" in out
    assert pipe.build_calls() == [f"{VIDEO_ID} {roster}"]


@needs_frame_tools
def test_a_beat_cut_entirely_needs_no_acknowledgement(pipe):
    """A redaction window that removes an unclean beat WHOLE is settled by
    geometry alone -- only the straddle case requires the owner's word."""
    manifest = pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([["hud"], [], [], []])
    pipe.write_redactions([{"id": "ratings_card",
                            "start_sec": 0.0,
                            "end_sec": float(manifest[0]["end_sec"]),
                            "reason": "ratings card, the whole frame",
                            "action": "cut", "boxes": "full"}])
    roster = pipe.write_roster()

    proc = pipe.run("--video-id", VIDEO_ID, roster)
    out = output(proc)

    assert proc.returncode == 0, out
    assert "REFUSING" not in out
    assert pipe.build_calls() == [f"{VIDEO_ID} {roster}"]


# ---------------------------------------------------------------------------
# 2. resume behaviour
# ---------------------------------------------------------------------------

def test_a_stage_whose_output_exists_is_skipped_and_reported(pipe):
    """Every stage skips when its output exists, which is what makes the
    script safe to re-run against a half-done video -- the normal state."""
    pipe.write_video_record()
    pipe.write_placeholder_media()
    pipe.write_manifest([
        {"start_sec": 0.0, "end_sec": 1.0, "start_tc": "0:00", "end_tc": "0:01"},
        {"start_sec": 1.0, "end_sec": 2.0, "start_tc": "0:01", "end_tc": "0:02"},
        {"start_sec": 2.0, "end_sec": 3.0, "start_tc": "0:02", "end_tc": "0:03"},
    ])

    proc = pipe.run("--video-id", VIDEO_ID)   # no tags: stops at stage 5
    out = output(proc)

    assert proc.returncode == 3, out
    assert f"(have media/{VIDEO_ID}.mp4, skipping)" in out
    assert f"(have keyframes/{VIDEO_ID}/beats.json, skipping)" in out
    assert "==> fetch" not in out, "fetch must not run against existing media"
    assert "==> detect beats and keyframes" not in out


# ---------------------------------------------------------------------------
# 3. the `automatable` stops
# ---------------------------------------------------------------------------

def test_automatable_no_stops_at_the_brief_and_stopping_is_a_success(pipe):
    """A visual judgement, a claim about a real person, or a licensing
    decision stops the pipeline AT THE BRIEF -- and stopping is the correct
    outcome (exit 0), never a failure to route around."""
    pipe.write_issue(f"""title: Stops at the brief
sources:
  - url: {WATCH_URL}
automatable: no
blocked_on: {BLOCKED_ON}
""")

    proc = pipe.run("42")
    out = output(proc)

    assert proc.returncode == 0, out
    assert "==> brief for issue #42" in out
    assert "not automatable" in out
    assert BLOCKED_ON in out, "the stop must say what would unblock it"
    assert "==> video_id" not in out, "nothing past the brief stage may run"


@needs_frame_tools
def test_automatable_partly_runs_the_mechanical_half_and_stops(pipe):
    """`partly` means indexing (the mechanical half) runs, but putting names
    on screen and shipping a file does not -- it stops before the credited
    build, exit 0, saying what it waits on."""
    pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], []])
    roster = pipe.write_roster()
    pipe.write_issue(f"""title: Partly automatable
sources:
  - url: {WATCH_URL}
    video_id: {VIDEO_ID}
automatable: partly
blocked_on: {BLOCKED_ON}
""")

    proc = pipe.run("42", roster)
    out = output(proc)

    assert proc.returncode == 0, out
    assert "==> assemble segments" in out, "the mechanical half should run"
    assert "automatable: partly, so it stops before the credited build" in out
    assert BLOCKED_ON in out
    assert pipe.build_calls() is None


# ---------------------------------------------------------------------------
# 4. music
# ---------------------------------------------------------------------------

@needs_frame_tools
def test_music_with_a_url_but_no_local_path_fails_loudly(pipe):
    """Nothing in the pipeline fetches audio. Rendering anyway would hand
    back a silent cut for a brief that asked for a score -- a failure that
    looks like an editorial choice -- so the script must refuse, loudly."""
    pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], []])
    roster = pipe.write_roster()
    pipe.write_issue(f"""title: Music without a local path
sources:
  - url: {WATCH_URL}
    video_id: {VIDEO_ID}
music:
  url: https://www.youtube.com/watch?v=MUSICTRACK1
  title: The Test Track
automatable: yes
""")

    proc = pipe.run("42", roster)
    out = output(proc)

    assert proc.returncode != 0, out
    assert "the brief asks for music but gives no local path" in out
    # ...and the message must say how to fetch it, not just that it failed.
    assert "yt-dlp -x --audio-format mp3" in out
    assert "https://www.youtube.com/watch?v=MUSICTRACK1" in out
    assert "path: media/<file>.mp3" in out
    assert pipe.build_calls() is None


@needs_frame_tools
def test_music_with_a_local_path_is_handed_to_the_build(pipe):
    """The other side of the distinction: a fetched track is passed to the
    credited build, so an unscored render is always the owner's choice."""
    pipe.write_clip_and_manifest()
    pipe.write_video_record()
    pipe.write_tags([[], [], [], []])
    roster = pipe.write_roster()
    pipe.write_issue(f"""title: Music with a local path
sources:
  - url: {WATCH_URL}
    video_id: {VIDEO_ID}
music:
  url: https://www.youtube.com/watch?v=MUSICTRACK1
  path: media/test_track.mp3
automatable: yes
""")

    proc = pipe.run("42", roster)
    out = output(proc)

    assert proc.returncode == 0, out
    assert pipe.build_calls() == [f"{VIDEO_ID} {roster} media/test_track.mp3"]


# ---------------------------------------------------------------------------
# 5. the URL-only brief
# ---------------------------------------------------------------------------

def test_a_url_only_brief_ingests_the_url_not_shifts_it_into_video_id(pipe):
    """The normal shape for a video nobody has ingested yet is a source with
    a `url` and no `video_id`. A `read -r VIDEO_ID SOURCE_URL` heredoc once
    collapsed the empty leading field and shifted the URL into VIDEO_ID, so
    the script looked for a video record named after a URL. This is that
    shape: ingest must run with the URL, and the id must resolve from the
    record ingest writes."""
    pipe.write_placeholder_media(INGESTED_ID)      # as if fetched earlier
    pipe.write_manifest(
        [{"start_sec": 0.0, "end_sec": 1.0, "start_tc": "0:00", "end_tc": "0:01"},
         {"start_sec": 1.0, "end_sec": 2.0, "start_tc": "0:01", "end_tc": "0:02"}],
        video_id=INGESTED_ID)
    pipe.write_issue(f"""title: Not yet ingested
sources:
  - url: {WATCH_URL}
    note: cinematics only
automatable: yes
""")

    proc = pipe.run("42")
    out = output(proc)

    assert f"==> ingest {WATCH_URL}" in out, out
    assert "no video record at" not in out, "the URL was shifted into VIDEO_ID"
    assert "ingest did not produce a video record" not in out
    assert f"==> video_id {INGESTED_ID}" in out
    # ...and the run then stops at tagging for THAT video (exit 3).
    assert proc.returncode == 3, out
    assert f"tags/{INGESTED_ID}.json is waiting: 2 beats to fill" in out
    assert f"one keyframe each in keyframes/{INGESTED_ID}/" in out
    record = pipe.root / "videos" / f"{INGESTED_ID}.json"
    assert record.exists(), "ingest never wrote a record"


# ---------------------------------------------------------------------------
# 6. stage 5 stops at tagging
# ---------------------------------------------------------------------------

def test_stage_5_stops_at_tagging_naming_the_keyframes_and_tag_file(pipe):
    """Tagging is the one stage a script cannot do: an untagged beat derives
    clean = false, and 'nobody has looked at this frame' is not evidence the
    frame is clean. The stop is deliberate, exit 3, and says what to write."""
    pipe.write_video_record()
    pipe.write_placeholder_media()
    pipe.write_manifest([
        {"start_sec": 0.0, "end_sec": 1.0, "start_tc": "0:00", "end_tc": "0:01"},
        {"start_sec": 1.0, "end_sec": 2.0, "start_tc": "0:01", "end_tc": "0:02"},
        {"start_sec": 2.0, "end_sec": 3.0, "start_tc": "0:02", "end_tc": "0:03"},
    ])

    proc = pipe.run("--video-id", VIDEO_ID)
    out = output(proc)

    assert proc.returncode == 3, out
    assert "Stopping at tagging, which is where a person looks at frames." in out
    # The stop names the keyframe count and the tag file path.
    assert (f"tags/{VIDEO_ID}.json is waiting: 3 beats to fill, one keyframe "
            f"each in keyframes/{VIDEO_ID}/") in out

    # The generated worksheet never pre-fills a judgement: every overlays is
    # null ("nobody has looked"), never [] ("this frame is clean"). A skeleton
    # that shipped [] would mark every untagged beat clean at the gate.
    worksheet = json.loads(
        (pipe.root / "tags" / f"{VIDEO_ID}.json").read_text())
    assert len(worksheet) == 3
    assert all(entry["overlays"] is None for entry in worksheet.values())
    assert all(entry["character"] is None for entry in worksheet.values())
