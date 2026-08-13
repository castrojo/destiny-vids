"""tools/farm.py — offloading an encode to the ghost cluster.

Offline by contract: the plan builder, the pod script, the manifest, the
availability gate and the verifier are all exercised without a cluster, an
ffmpeg, or a network. The two tests that really encode are gated — one on a
runnable local ffmpeg, one on a reachable cluster — so CI (neither) skips
them.
"""
import json
import os
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


def test_the_workflow_is_a_plain_workflow_pinned_to_exo0():
    wf = farm.build_workflow("farm-x-ab12", "echo hi",
                             namespace="argo", image=farm.DEFAULT_IMAGE,
                             cpu="2", limit_cpu="24", memory="4Gi",
                             limit_memory="16Gi", node="exo-0",
                             service_account="argo", keep=False)
    assert wf["kind"] == "Workflow"  # a WorkflowTemplate would be GitOps'd
    spec = wf["spec"]
    assert spec["serviceAccountName"] == "argo"
    tpl = spec["templates"][0]
    # exo-0 has ~24 free cores; ghost only ~14.
    assert tpl["nodeSelector"] == {"kubernetes.io/hostname": "exo-0"}
    res = tpl["container"]["resources"]
    # House style: a low request always schedules, the high limit is the real
    # budget on an idle node (the cluster runs at 156-263% limit overcommit).
    assert res["requests"] == {"cpu": "2", "memory": "4Gi"}
    assert res["limits"] == {"cpu": "24", "memory": "16Gi"}
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
                             node="exo-0", service_account="argo", keep=True)
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
    src = tmp_path / "in.mp4"
    src.write_bytes(b"footage" * 100)
    plan = farm.build_plan(facts=facts(duration=4.0, frame_count=120),
                           out_name="o.mp4", segments=3, video_args=[],
                           audio_args=[], threads=6,
                           work_dir=str(tmp_path / "w"), src_arg=str(src),
                           ffmpeg=tuple(_fake_ffmpeg(tmp_path)))
    farm.run_locally(plan, workers=2)
    out = Path(plan["join"][-1])
    assert out.read_bytes() == b"footage" * 100 * 3
    # Progress files were written, which is what the monitor thread reads.
    assert list((tmp_path / "w" / "logs").glob("*.progress"))


def test_local_run_reports_a_failing_chunk(tmp_path, monkeypatch):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"x")
    plan = farm.build_plan(facts=facts(), out_name="o.mp4", segments=2,
                           video_args=[], audio_args=[], threads=6,
                           work_dir=str(tmp_path / "w"), src_arg=str(src),
                           ffmpeg=("false",))
    with pytest.raises(farm.FarmError, match="chunk"):
        farm.run_locally(plan, workers=2)


# --------------------------------------------------------------------------
# Gated live checks: these skip anywhere but the owner's setup.


def _local_ffmpeg():
    try:
        ffmpeg = farm.find_ffmpeg()
    except RuntimeError:
        pytest.skip("no ffmpeg available")
    try:
        import subprocess
        subprocess.run([*ffmpeg, "-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg is not runnable here")
    return ffmpeg


def test_local_fallback_actually_encodes(tmp_path):
    """The --local path end to end, gated on a real ffmpeg (skipped in CI).

    The fixture lives under $HOME because the resolved ffmpeg is a container
    that cannot see pytest's /var/tmp (docs/rendering.md).
    """
    ffmpeg = _local_ffmpeg()
    import subprocess
    work = Path.home() / ".cache" / "destiny-vids-farm-test"
    work.mkdir(parents=True, exist_ok=True)
    src = work / "src.mp4"
    subprocess.run([*ffmpeg, "-nostdin", "-f", "lavfi", "-i",
                    "testsrc2=size=320x240:rate=30:duration=4", "-pix_fmt",
                    "yuv420p", "-c:v", "libx264", "-y", str(src)],
                   check=True, capture_output=True)
    out = work / "out.mp4"
    rc = farm.main([str(src), "--out", str(out), "--local", "--segments", "2",
                    "--", "-c:v", "libx264", "-crf", "28", "-preset",
                    "ultrafast", "-an"])
    assert rc == 0
    assert out.exists()


@pytest.mark.skipif(os.environ.get("DESTINY_FARM_E2E") != "1",
                    reason="live cluster encode; set DESTINY_FARM_E2E=1")
def test_cluster_roundtrip(tmp_path):
    ok, why = farm.cluster_available()
    if not ok:
        pytest.skip(f"cluster unreachable: {why}")
    _local_ffmpeg()  # the fixture clip is preflighted locally
    media = sorted(Path(os.environ.get(
        "DESTINY_MEDIA", Path.home() / "src/destiny-vids/media")).glob("*.mp4"),
        key=lambda p: p.stat().st_size)
    if not media:
        pytest.skip("no media/*.mp4 to encode")
    out = Path.home() / ".cache" / "destiny-vids-farm-test" / "cluster.mp4"
    rc = farm.main([str(media[0]), "--out", str(out), "--segments", "2",
                    "--", "-c:v", "libx264", "-crf", "28", "-preset",
                    "ultrafast", "-c:a", "aac", "-b:a", "96k"])
    assert rc == 0 and out.exists()
