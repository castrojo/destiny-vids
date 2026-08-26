"""tools/farm.py — offloading an encode to the ghost cluster.

Offline by contract: the plan builder, the pod script, the manifest, the
availability gate and the verifier are all exercised without a cluster, an
ffmpeg, or a network. The two tests that really encode are gated — one on a
runnable local ffmpeg, one on a reachable cluster — so CI (neither) skips
them.
"""
import json
import os
import re
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from tools import farm  # noqa: E402

FACTS = {
    "duration": 111.6, "fps": Fraction(30, 1), "vfr": False,
    "frame_count": 3348, "codec_name": "h264", "width": 1920,
    "height": 1080, "pix_fmt": "yuv420p", "stream_kinds": ["video", "audio"],
}

def facts(**over):
    return {**FACTS, **over}

# --------------------------------------------------------------------------
# chunk boundaries: the seam arithmetic is the whole ballgame

def test_boundaries_cover_the_file_exactly_on_the_frame_grid():
    spans = farm.chunk_boundaries(facts(), 4)
    assert len(spans) == 4
    assert spans[0][0] == 0.0
    # No gaps, no overlaps.
    for (ss, dur, _), (next_ss, _, _) in zip(spans, spans[1:]):
        assert abs(ss + dur - next_ss) < 1e-9
    assert abs(spans[-1][0] + spans[-1][1] - 111.6) < 1e-9
    # Every boundary is an exact multiple of the frame period, and the frame
    # counts are integers summing to the whole file.
    assert sum(n for _, _, n in spans) == 3348
    for ss, dur, n in spans:
        assert isinstance(n, int)
        for t in (ss, dur):
            frames = t * 30
            assert abs(frames - round(frames)) < 1e-6

def test_boundaries_clamp_to_the_frame_count():
    spans = farm.chunk_boundaries(facts(duration=0.1, frame_count=3), 8)
    assert len(spans) == 3

def test_a_vfr_source_falls_back_to_time_slices():
    spans = farm.chunk_boundaries(facts(vfr=True), 3)
    assert [round(d, 3) for _, d, n in spans] == [37.2, 37.2, 37.2]
    assert all(n is None for _, _, n in spans)

def test_cfr_chunks_encode_an_exact_integer_frame_count():
    """issue-#88-class bug, measured on act VI: a float -t truncates into the
    stream timebase and drops the seam frame (13297 vs 13301)."""
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=4,
                           video_args=[], audio_args=[], threads=6,
                           work_dir="/w", src_arg="/w/in/s.mp4")
    counts = []
    for c in plan["chunks"]:
        argv = c["argv"]
        assert "-t" not in argv, "CFR chunks must not use a float duration"
        counts.append(int(argv[argv.index("-frames:v") + 1]))
    assert sum(counts) == 3348

# --------------------------------------------------------------------------
# the plan

def test_chunk_commands_seek_input_side_and_force_threads_after_the_recipe():
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=2,
                           video_args=["-c:v", "libx264", "-threads", "99"],
                           audio_args=[], threads=6, work_dir="/work",
                           src_arg="/work/in/s.mp4")
    for c in plan["chunks"]:
        argv = c["argv"]
        # -ss before -i: input-side seek, timestamps rebased to zero.
        assert argv.index("-ss") < argv.index("-i")
        # The farm's -threads comes after the recipe so it wins.
        last = len(argv) - 1 - argv[::-1].index("-threads")
        assert argv[last + 1] == "6"
        assert last > argv.index("99")
        assert "-progress" in argv

def test_join_is_stream_copy_and_faststart_for_mp4_only():
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=2,
                           video_args=[], audio_args=[], threads=6,
                           work_dir="/w", src_arg="/w/in/s.mp4")
    join = plan["join"]
    assert join[join.index("-c") + 1] == "copy"
    assert "+faststart" in join
    mkv = farm.build_plan(facts=facts(), out_name="o.mkv", segments=2,
                          video_args=[], audio_args=[], threads=6,
                          work_dir="/w", src_arg="/w/in/s.mp4")
    assert "+faststart" not in mkv["join"]

def test_concat_list_matches_the_chunks_in_order():
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=3,
                           video_args=[], audio_args=[], threads=6,
                           work_dir="/w", src_arg="/w/in/s.mp4")
    assert plan["concat_list"] == [f"/w/chunks/chunk_{i:04d}.mp4"
                                   for i in range(3)]

# --------------------------------------------------------------------------
# the pod script

def test_pod_script_is_valid_bash_and_waits_for_both_markers(tmp_path):
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=3,
                           video_args=farm.DEFAULT_VIDEO_ARGS, audio_args=farm.DEFAULT_AUDIO_ARGS, threads=6,
                           work_dir=farm.WORK_DIR, src_arg="/work/in/s.mp4")
    script = farm.pod_script(plan)
    assert "in/.ready" in script and ".fetched" in script
    assert script.count("pids+=($!)") == 4  # 3 chunks + the audio pass
    assert " -an " in script  # chunks are video-only; audio is one pass
    assert "audio.mkv" in script and "-map" in script
    assert "outputs.artifacts" not in script  # no artifact repo exists
    script_file = tmp_path / "pod.sh"
    script_file.write_text(script)
    import shutil
    import subprocess
    if shutil.which("bash"):
        proc = subprocess.run(["bash", "-n", str(script_file)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr

# --------------------------------------------------------------------------
# the manifest

def test_the_workflow_is_plain_scheduler_driven_and_admission_compliant():
    wf = farm.build_workflow("farm-x-ab12", "echo hi",
                             namespace="argo", image=farm.DEFAULT_IMAGE,
                             cpu="2", limit_cpu="24", memory="4Gi",
                             limit_memory="16Gi", node=None, keep=False)
    assert wf["kind"] == "Workflow"  # a WorkflowTemplate would be GitOps'd
    spec = wf["spec"]
    assert spec["serviceAccountName"] == "argo"
    tpl = spec["templates"][0]
    assert "nodeSelector" not in tpl
    res = tpl["container"]["resources"]
    # House style: a low request always schedules, the high limit is the real
    # budget on an idle node (the cluster runs at 156-263% limit overcommit).
    assert res["requests"] == {
        "cpu": "2", "memory": "4Gi", "ephemeral-storage": "1Gi"}
    assert res["limits"] == {
        "cpu": "24", "memory": "16Gi", "ephemeral-storage": "4Gi"}
    assert tpl["container"]["imagePullPolicy"] == "IfNotPresent"
    assert tpl["container"]["command"][:2] == ["/bin/bash", "-c"]
    assert spec["volumes"][0]["persistentVolumeClaim"]["claimName"] == "farm-x-ab12"
    # No artifacts section anywhere: the cluster has no artifact repository.
    assert "artifacts" not in json.dumps(wf)
    assert "amd.com/gpu" not in json.dumps(wf)  # CPU-only: faster AND better
    assert spec["ttlStrategy"]["secondsAfterSuccess"] == 3600

def test_keep_omits_the_ttl_backstop():
    wf = farm.build_workflow("farm-x-ab12", "s", namespace="argo", image="i",
                             cpu="1", limit_cpu="1", memory="1Gi",
                             limit_memory="2Gi",
                             node="exo-0", keep=True)
    assert "ttlStrategy" not in wf["spec"]

def test_the_default_image_is_pullable_through_the_zot_allowlist():
    """ghcr.io/jrottenberg/ffmpeg is NOT reachable on this cluster: the zot
    mirror syncs tags only (lab ADR 0007), ghcr has no jrottenberg tag past
    6.0, and jrottenberg/* is not in the sync allowlist. lscr.io is
    allowlisted wholesale, and linuxserver/ffmpeg is the same full non-free
    build — verified pulling on the cluster."""
    assert farm.DEFAULT_IMAGE == "lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76"
    assert "@sha256:" not in farm.DEFAULT_IMAGE  # digests 404 through zot

def test_pvc_is_local_path_rwo():
    pvc = farm.build_pvc("farm-x-ab12", namespace="argo", storage="4Gi")
    assert pvc["spec"]["storageClassName"] == "local-path"
    assert pvc["spec"]["accessModes"] == ["ReadWriteOnce"]

def test_pod_blocker_surfaces_unschedulable_and_image_errors():
    unsched = {"status": {"conditions": [{
        "type": "PodScheduled", "status": "False", "reason": "Unschedulable",
        "message": "0/2 nodes are available: insufficient cpu."}]}}
    assert "unschedulable" in farm.pod_blocker(unsched)
    pull = {"status": {"containerStatuses": [{
        "name": "main",
        "state": {"waiting": {"reason": "ImagePullBackOff",
                              "message": "not found"}}}]}}
    assert "ImagePullBackOff" in farm.pod_blocker(pull)
    running = {"status": {"containerStatuses": [{
        "name": "main", "state": {"running": {}}}]}}
    assert farm.pod_blocker(running) is None

def test_storage_scales_with_the_source():
    assert farm.storage_for(100 * 1024 ** 2) == "1Gi"
    assert farm.storage_for(2 * 1024 ** 3) == "6Gi"

# --------------------------------------------------------------------------
# availability and verification

def test_cluster_unavailable_when_kubectl_is_missing(monkeypatch):
    monkeypatch.setattr(farm.shutil, "which", lambda _: None)
    ok, why = farm.cluster_available()
    assert not ok and "kubectl" in why

def test_cluster_unavailable_when_the_api_errors(monkeypatch):
    monkeypatch.setattr(farm.shutil, "which", lambda _: "/usr/bin/kubectl")

    class FakeKubectl:
        def __init__(self, *a, **k):
            pass

        def run(self, args, **k):
            class P:
                returncode = 1
                stderr = "The connection to the server 192.168.1.102:6443 was refused"
                stdout = ""
            return P()

    monkeypatch.setattr(farm, "Kubectl", FakeKubectl)
    ok, why = farm.cluster_available()
    assert not ok and "refused" in why

def _probe_doc(duration, frames="600", codec="h264", fps="30/1",
               kinds=("video", "audio")):
    streams = []
    for kind in kinds:
        s = {"codec_type": kind, "codec_name": codec if kind == "video" else "flac",
             "r_frame_rate": fps, "avg_frame_rate": fps}
        if kind == "video":
            s.update(width=1920, height=1080, pix_fmt="yuv420p",
                     duration=str(duration), nb_frames=frames)
        streams.append(s)
    return {"streams": streams, "format": {"duration": str(duration)}}

def test_probe_parses_the_video_stream(monkeypatch, tmp_path):
    import subprocess as sp
    doc = _probe_doc(20.0)
    monkeypatch.setattr(sp, "run", lambda *a, **k: type(
        "P", (), {"returncode": 0, "stdout": json.dumps(doc), "stderr": ""})())
    f = farm.probe(tmp_path / "x.mp4", ["ffprobe"])
    assert f["duration"] == 20.0 and f["frame_count"] == 600
    assert f["fps"] == Fraction(30, 1)

def test_verify_catches_a_short_file_and_a_dropped_stream(monkeypatch):
    """issue #88: ffmpeg exited 0 and shipped a file 8.5s short."""
    def fake_probe(path, _):
        if "out" in str(path):
            return {"duration": 103.1, "fps": Fraction(30),
                    "frame_count": 3093, "codec_name": "h264", "width": 1920,
                    "height": 1080, "pix_fmt": "yuv420p",
                    "stream_kinds": ["video"]}
        return {"duration": 111.6, "fps": Fraction(30), "frame_count": 3348,
                "codec_name": "h264", "width": 1920, "height": 1080,
                "pix_fmt": "yuv420p", "stream_kinds": ["video", "audio"]}
    monkeypatch.setattr(farm, "probe", fake_probe)
    problems = farm.verify_output("out.mp4", "src.mp4", ffprobe=["x"],
                                  strict_streams=False)
    assert any("duration" in p for p in problems)
    assert any("stream count" in p for p in problems)
    assert any("frame count" in p for p in problems)

def test_verify_passes_a_matching_output(monkeypatch):
    good = {"duration": 111.63, "fps": Fraction(30), "frame_count": 3348,
            "codec_name": "h264", "width": 1920, "height": 1080,
            "pix_fmt": "yuv420p", "stream_kinds": ["video", "audio"]}
    monkeypatch.setattr(farm, "probe", lambda path, _: dict(good))
    assert farm.verify_output("out.mp4", "ref.mp4", ffprobe=["x"],
                              strict_streams=True) == []

def test_strict_streams_only_against_an_explicit_reference(monkeypatch):
    """A recipe that legitimately scales must not fail against the source."""
    scaled = {"duration": 111.6, "fps": Fraction(30), "frame_count": 3348,
              "codec_name": "h264", "width": 1280, "height": 720,
              "pix_fmt": "yuv420p", "stream_kinds": ["video", "audio"]}
    source = {"duration": 111.6, "fps": Fraction(30), "frame_count": 3348,
              "codec_name": "h264", "width": 1920, "height": 1080,
              "pix_fmt": "yuv420p", "stream_kinds": ["video", "audio"]}
    monkeypatch.setattr(
        farm, "probe",
        lambda path, _: scaled if "out" in str(path) else source)
    assert farm.verify_output("out.mp4", "src.mp4", ffprobe=["x"],
                              strict_streams=False) == []
    assert farm.verify_output("out.mp4", "src.mp4", ffprobe=["x"],
                              strict_streams=True) != []

# --------------------------------------------------------------------------
# local executor, with a fake ffmpeg: offline, hermetic, and it still proves
# the chunk -> join -> output flow end to end.

def _fake_ffmpeg(tmp_path):
    """A stand-in ffmpeg that copies -i to the output, and concatenates for
    the join, so the local executor's plumbing is really exercised."""
    exe = tmp_path / "fake-ffmpeg"
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "a = sys.argv[1:]\n"
        "out = a[a.index('-y') + 1]\n"
        "if '-f' in a and a[a.index('-f') + 1] == 'concat':\n"
        "    lst = open(a[a.index('-i') + 1]).read().splitlines()\n"
        "    data = b''.join(open(l.split(\"'\")[1], 'rb').read() for l in lst)\n"
        "else:\n"
        "    data = open(a[a.index('-i') + 1], 'rb').read()\n"
        "if '-progress' in a:\n"
        "    open(a[a.index('-progress') + 1], 'w').write('out_time_us=1000000\\n')\n"
        "open(out, 'wb').write(data)\n")
    exe.chmod(0o755)
    return [str(exe)]

def test_local_run_executes_chunks_and_join(tmp_path, monkeypatch):
    with pytest.raises(farm.FarmError, match="prohibited"):
        farm.run_locally({}, workers=2)

def test_local_run_reports_a_failing_chunk(tmp_path, monkeypatch):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=2,
                           video_args=[], audio_args=[], threads=6,
                           work_dir=str(tmp_path / "w"), src_arg=str(src),
                           ffmpeg=("false",))
    with pytest.raises(farm.FarmError, match="prohibited"):
        farm.run_locally(plan, workers=2)

# --------------------------------------------------------------------------
# The generic one-argv capability (run_ffmpeg_on_cluster): megacut's ENCODE
# segments ride this. Offline like everything above — the kubectl layer is
# faked, the pod never exists.

import subprocess  # noqa: E402  (module-level: the fakes below use it)

def test_rewrite_argv_maps_binary_inputs_and_output():
    argv = ["/home/linuxbrew/.linuxbrew/bin/ffmpeg", "-nostdin", "-i",
            "/abs/act.mp4", "-vf", "fps=60000/1001,trim=end=431.231",
            "-c:v", "libx264", "/abs/seg009.mkv", "-y"]
    pod_argv, uploads, pod_out = farm.rewrite_argv_for_pod(
        argv, ["/abs/act.mp4"], "/abs/seg009.mkv")
    # The local binary travels nowhere; the image's ffmpeg runs the recipe.
    assert pod_argv[0] == "ffmpeg"
    assert "/home/linuxbrew" not in " ".join(pod_argv)
    assert pod_argv[pod_argv.index("-i") + 1] == "/work/in/00-act.mp4"
    assert "/work/out/seg009.mkv" in pod_argv
    assert pod_out == "/work/out/seg009.mkv"
    assert uploads == [(Path("/abs/act.mp4"), "in/00-act.mp4")]
    # A path inside a FILTER string is not rewritten (megacut's chains carry
    # none) — and the rest of the recipe travels byte-for-byte.
    assert "fps=60000/1001,trim=end=431.231" in pod_argv

def test_rewrite_argv_strips_a_multi_token_container_launcher():
    # find_ffmpeg() does not always return a bare binary: on an atomic
    # Fedora/Bluefin host the system ffmpeg is ffmpeg-free with no H.264, so
    # the resolver hands back `podman exec bluefin-thumbnailer ffmpeg`.
    # Replacing only argv[0] left `exec bluefin-thumbnailer ffmpeg` as stray
    # positionals, ffmpeg took the last as the output file, and act 0's farm
    # encode died with "Unable to choose an output format for 'exec'".
    argv = ["podman", "exec", "bluefin-thumbnailer", "ffmpeg",
            "-hide_banner", "-y", "-i", "/abs/src.mkv",
            "-c:v", "libx264", "/abs/00-prologue.mp4"]
    pod_argv, _, pod_out = farm.rewrite_argv_for_pod(
        argv, ["/abs/src.mkv"], "/abs/00-prologue.mp4")
    assert pod_argv[0] == "ffmpeg"
    # The launcher leaves NO residue: these tokens must not survive as args.
    for stray in ("podman", "exec", "bluefin-thumbnailer"):
        assert stray not in pod_argv
    assert pod_argv[1] == "-hide_banner"
    assert pod_argv[pod_argv.index("-i") + 1] == "/work/in/00-src.mkv"
    assert pod_out == "/work/out/00-prologue.mp4"
    assert pod_argv[-1] == pod_out


def test_rewrite_argv_keeps_a_bare_binary_working():
    # The one-token shape must still behave: the fix generalises argv[0],
    # it does not trade one launcher shape for another.
    pod_argv, _, _ = farm.rewrite_argv_for_pod(
        ["ffmpeg", "-i", "/a/s.mkv", "/o/o.mp4"], ["/a/s.mkv"], "/o/o.mp4")
    assert pod_argv == ["ffmpeg", "-i", "/work/in/00-s.mkv",
                        "/work/out/o.mp4"]


def test_rewrite_argv_rejects_an_argv_that_names_no_ffmpeg():
    # An argv opening on an option has no launcher to replace; stripping
    # nothing would silently prepend `ffmpeg` to a recipe missing its own.
    with pytest.raises(farm.FarmError, match="names no ffmpeg"):
        farm.rewrite_argv_for_pod(
            ["-i", "/a/s.mkv", "/o/o.mp4"], ["/a/s.mkv"], "/o/o.mp4")


def test_rewrite_argv_stages_same_named_inputs_distinctly():
    argv = ["ffmpeg", "-i", "/a/seg.mp4", "-i", "/b/seg.mp4",
            "/out/o.mkv", "-y"]
    pod_argv, uploads, _ = farm.rewrite_argv_for_pod(
        argv, ["/a/seg.mp4", "/b/seg.mp4"], "/out/o.mkv")
    assert uploads == [(Path("/a/seg.mp4"), "in/00-seg.mp4"),
                       (Path("/b/seg.mp4"), "in/01-seg.mp4")]
    assert "/work/in/00-seg.mp4" in pod_argv
    assert "/work/in/01-seg.mp4" in pod_argv


def test_rewrite_argv_strips_glob_metacharacters_from_staging_names():
    # kubectl cp glob-expands the remote path: a bracketed name delivers
    # nothing with exit 0 (act VII's bed never landed). Spaces are safe.
    bed = "/d/Beauty Of The Beast [X3WrCzLIIvk].webm"
    pod_argv, uploads, pod_out = farm.rewrite_argv_for_pod(
        ["ffmpeg", "-i", bed, "/o/07-europa [dc].mp4"], [bed],
        "/o/07-europa [dc].mp4")
    staged = uploads[0][1]
    assert staged == "in/00-Beauty Of The Beast _X3WrCzLIIvk_.webm"
    assert pod_argv[pod_argv.index("-i") + 1] == f"/work/{staged}"
    assert pod_out == "/work/out/07-europa _dc_.mp4"


def test_an_image_sequence_pattern_is_staged_as_its_frames(tmp_path):
    """A %0Nd input must reach the pod, or a plate burn cannot be farmed.

    The exact-token guard cannot see a pattern's frames -- they never appear
    in argv -- so before this the burn was rejected and the caller fell back
    to encoding locally on the owner's workstation.
    """
    from tools import farm

    seq = tmp_path / "plate_%02d.png"
    for i in range(3):
        (tmp_path / f"plate_{i:02d}.png").write_bytes(b"x")
    video = tmp_path / "in.mp4"
    video.write_bytes(b"v")
    out = tmp_path / "out.mp4"

    argv = ["/local/ffmpeg", "-i", str(video), "-i", str(seq), str(out)]
    pod_argv, uploads, pod_out = farm.rewrite_argv_for_pod(
        argv, [video, seq], out)

    # every frame is staged, into one directory
    staged = [rel for _, rel in uploads if rel.endswith(".png")]
    assert len(staged) == 3, staged
    assert len({r.rsplit("/", 1)[0] for r in staged}) == 1

    # and the pattern still reads as a pattern inside the pod
    pattern_tok = [t for t in pod_argv if t.endswith("plate_%02d.png")]
    assert len(pattern_tok) == 1, pod_argv
    assert pattern_tok[0].startswith(farm.WORK_DIR)


def test_the_chunked_path_stages_a_glob_free_name(monkeypatch):
    """run_on_cluster is the chunked single-file CLI: it must stage under the
    same glob-free name build_plan wrote into the script, or kubectl cp
    delivers nothing and the pod encodes an empty in/ (the 4c0bc0c fix only
    covered rewrite_argv_for_pod)."""
    captured = {}
    monkeypatch.setattr(farm, "_execute_on_cluster",
                        lambda **kw: captured.update(kw) or 0)
    src = "/d/Beauty Of The Beast [X3WrCzLIIvk].webm"
    farm.run_on_cluster({"out_rel": "out/o.mp4", "chunks": [1, 2]},
                        name="n", src=src,
                        out="/o/o.mp4", script="s", kc=None, image="i",
                        cpu=1, limit_cpu=1, memory="1Gi", limit_memory="1Gi",
                        node="n", storage="1Gi", keep=False, timeout=1)
    (local, rel), = captured["uploads"]
    assert local == src
    assert rel == "in/Beauty Of The Beast _X3WrCzLIIvk_.webm"
    assert not re.search(r"[\[\]*?]", rel)
