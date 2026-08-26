"""The farm-first encoding policy, asserted statically over tools/ and scripts/.

AGENTS.md: "always prefer remote encoding when available." A video encode that
reaches ``subprocess.run`` directly is the failure that OOM-killed the owner's
workstation at 03:08Z on 2026-08-24 (a bare local x264 run of a 7+ minute act
in scripts/build_credits.py): uncapped, and silent about being local at all.

After the farm-first sweep, EVERY video encode flows through tools/farm.py's
remote posture: ``run_ffmpeg_on_cluster`` /
``run_ffmpeg_commands_on_cluster`` /
``run_ffmpeg_chain_on_cluster`` on the farm. This file pins that in two
directions:

* INVENTORY -- every known video-encode entry point must reference the farm
  posture in its code (not its docstring). This is the backbone: it fails on
  the pre-sweep shape, where each of these functions shelled out to ffmpeg
  directly.
* The SWEEP -- any function carrying a video-encode marker (an x264/x265
  recipe or the delivery spec's argv builder) AND a bare subprocess call that
  the inventory and the audio-only whitelist do not explain is a new bypass
  and fails the suite.

Audio-only ffmpeg calls -- the ones that stream-copy the picture or never
touch it -- are EXEMPT, and the whitelist says why for each. The suite is
offline: everything here is source inspection (tests/conftest.py keeps the
cluster and systemd-run out of every test).
"""

import ast
from pathlib import Path

import pytest

from tools import farm  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

VIDEO_MARKERS = ('"libx264"', '"libx265"', "video_encode_args",
                 '"-c:v"', "'-c:v'")

# The farm posture, as token references in a function's CODE (docstrings are
# stripped before the check -- a mention in prose is not a route).
FARM_MARKERS = ("run_ffmpeg_on_cluster",
                "run_ffmpeg_commands_on_cluster",
                "run_ffmpeg_chain_on_cluster", "cluster_available",
                "run_encode")

# Every entry point that encodes VIDEO, and why it is allowed to. Each must
# reference the farm posture; ``via=`` names the helper it delegates the
# posture to instead.
FARMED = {
    ("tools/plate.py", "burn"): "the burn runs on the farm",
    ("tools/plate.py", "main"): "the burn CLI farms and rejects --local",
    ("tools/conform.py", "ensure"): "delegates the encode to _encode",
    ("tools/conform.py", "_encode"): "the conform cache encodes on the farm",
    ("tools/render.py", "still_clip"): "farm executor",
    ("tools/render.py", "cut_clip"): "farm executor",
    ("tools/render.py", "concat"): "farm executor",
    ("tools/render.py", "render"): "the cut chains to one farm pod by default",
    ("tools/redact.py", "apply"): "the drawbox pass farms by default",
    ("tools/megacut.py", "_segment_worker"): "segment executor",
    ("tools/megacut.py", "_farm_segment_worker"): "segments farm by default",
    ("tools/social.py", "main"): "both passes share one farm pod",
    ("tools/farm.py", "run_locally"): "the local path is rejected",
    ("scripts/actbuild.py", "main"): "acts IV/V/VII farm by default",
    ("scripts/build_act1.py", "build_act1"): "act I's legs farm by default",
    ("scripts/build_credits.py", "main"): "the 03:08Z crasher itself",
    ("scripts/build_efmb.py", "_run"): "every act II step farms via "
    "run_encode",
    ("scripts/build_efmb.py", "render"): "act II's parts chain to one pod",
    ("scripts/build_ending_overlays.py", "main"): "the derivative farms",
    ("scripts/build_ending_pause.py", "main"): "the pause farms",
    ("scripts/build_interludes.py", "main"): "the movements farm",
    ("scripts/build_intermission.py", "render"): "the deck farms (and "
    "cluster_available's tuple is unpacked)",
    ("scripts/build_europa.py", "main"): "the master farms",
    ("scripts/build_prologue.py", "encode"): "the prologue farms",
    ("scripts/build_prologue.py", "main"): "the --local path is rejected",
    ("scripts/build_trailer1.py", "main"): "the trailer farms, reruns too",
}
# A via= entry passes when it calls the named helper, which is itself in
# FARMED and must carry a marker.
FARMED_VIA = {
    ("tools/conform.py", "ensure"): "_encode(",
}

# Audio-only ffmpeg calls: the picture is stream-copied or absent, so they are
# remuxes, not encodes. The token is asserted present, so an exempt function
# that STARTS encoding video fails here.
EXEMPT_AUDIO_ONLY = {
    ("tools/audiomix.py", "mux"): '"-c:v", "copy"',
    ("tools/peaks.py", "rerun"): '"-c:v", "copy"',
    ("tools/bed.py", "render_bed"): '"-map", "[out]"',
    ("tools/megacut.py", "assemble"): "build_concat_command(",
}


def _functions(path):
    """{qualified name: (code-only source, [subprocess/os.system call lines])}.

    The docstring is blanked out of the source so a prose mention of a farm
    helper cannot satisfy the policy -- only a route can.
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = {}

    def visit(node, prefix=()):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = ".".join((*prefix, child.name))
                segment = ast.get_source_segment(src, child) or ""
                # Blank the docstring by its exact span: get_docstring()
                # returns the CLEANED text, which does not match the raw
                # indented source, and a prose mention of a farm helper must
                # not count as a route.
                doc_node = (child.body[0] if child.body
                            and isinstance(child.body[0], ast.Expr)
                            and isinstance(child.body[0].value, ast.Constant)
                            and isinstance(child.body[0].value.value, str)
                            else None)
                if doc_node is not None:
                    segment = segment.replace(
                        ast.get_source_segment(src, doc_node), "", 1)
                # A call is attributed to its INNERMOST function only: a
                # closure's subprocess is the closure's entry, not the outer
                # function's (peaks.py's `rerun` is the classic shape).
                calls = []

                def own_calls(n):
                    for c in ast.iter_child_nodes(n):
                        if isinstance(c, (ast.FunctionDef,
                                          ast.AsyncFunctionDef)):
                            continue
                        if isinstance(c, ast.Call) and isinstance(
                                c.func, ast.Attribute) and isinstance(
                                c.func.value, ast.Name) and (
                                f"{c.func.value.id}.{c.func.attr}"
                                in ("subprocess.run", "subprocess.Popen",
                                    "subprocess.call", "os.system")):
                            calls.append(c.lineno)
                        own_calls(c)

                own_calls(child)
                found[(child.name, qual)] = (segment, calls)
                visit(child, (*prefix, child.name))
            else:
                visit(child, prefix)

    visit(tree)
    # The flat view the policy tables use: the innermost function's name is
    # the key (the tables name files too, so cross-module collisions can't).
    return {qual.split(".")[-1]: v for (_name, qual), v in found.items()}


def _python_entry_points():
    return sorted(REPO_ROOT.glob("tools/*.py")) + \
        sorted(REPO_ROOT.glob("scripts/*.py"))


def test_every_known_video_encode_references_the_farm_posture():
    """The inventory: today's list of places a video encode executes. Each
    one must route through tools/farm.py -- this is the assertion that fails
    on the pre-sweep shape, where every one of these called subprocess.run
    on a bare x264 argv."""
    problems = []
    for (rel, func), why in sorted(FARMED.items()):
        funcs = _functions(REPO_ROOT / rel)
        assert func in funcs, f"{rel}::{func} does not exist -- the " \
            f"inventory is stale ({why})"
        code, _calls = funcs[func]
        via = FARMED_VIA.get((rel, func))
        markers = (via,) if via else FARM_MARKERS
        if not any(m in code for m in markers):
            problems.append(f"{rel}::{func} ({why})")
    assert not problems, (
        "video encode entry point(s) with no route through tools/farm.py's "
        "posture (run_ffmpeg_on_cluster / run_ffmpeg_chain_on_cluster / "
        "run_encode / cluster_available):\n  "
        + "\n  ".join(problems)
        + "\nAGENTS.md: always prefer remote encoding when available; local "
          "ffmpeg execution is prohibited, so the farm route is the only "
          "one there is.")


def test_no_unclassified_video_encode_subprocess_call():
    """The sweep: a function that builds a video encode AND shells out must
    be explained -- by the inventory above or the audio-only whitelist."""
    violations = []
    for path in _python_entry_points():
        rel = str(path.relative_to(REPO_ROOT))
        for func, (code, calls) in _functions(path).items():
            if not calls:
                continue
            if not any(m in code for m in VIDEO_MARKERS):
                continue
            if (rel, func) in FARMED:
                continue
            if (rel, func) in EXEMPT_AUDIO_ONLY:
                continue
            violations.append(f"{rel}::{func} (subprocess at lines "
                              f"{', '.join(map(str, calls))})")
    assert not violations, (
        "video encode(s) that bypass the farm posture and are not on the "
        "audio-only exempt list:\n  " + "\n  ".join(violations))


def test_cluster_available_is_unpacked_not_truthiness_tested():
    """scripts/build_intermission.py tested ``if farm.cluster_available():``
    -- and the helper returns a TUPLE, which is always truthy, so the deck
    "fell back" to the farm on a down cluster forever. The result is always
    unpacked: ``ok, why = farm.cluster_available()``."""
    import re
    offenders = []
    for path in _python_entry_points():
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\bif\b[^\n=]*\bcluster_available\(\)", line):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "cluster_available() returns (ok, why) -- testing the tuple with "
        "`if` is always true:\n  " + "\n  ".join(offenders))


def test_the_audio_only_exemptions_still_copy_the_picture():
    """An exemption is a remux, not an encode: the day one of these grows a
    video encoder it must move to the farmed inventory, and this fails."""
    drifted = []
    for (rel, func), token in sorted(EXEMPT_AUDIO_ONLY.items()):
        code, _ = _functions(REPO_ROOT / rel)[func]
        if token not in code:
            drifted.append(f"{rel}::{func} no longer carries {token}")
        if any(m in code for m in ('"libx264"', '"libx265"',
                                   "video_encode_args")):
            drifted.append(f"{rel}::{func} now ENCODES video -- move it to "
                           "the farmed inventory")
    assert not drifted, "\n".join(drifted)


def test_the_shell_pipelines_carry_the_escape_hatch():
    """The two shell entry points pass --local through to the tools, which
    own the farm decision themselves now."""
    uncut = (REPO_ROOT / "scripts" / "build_uncut_credited.sh").read_text()
    assert "LOCAL_OPT" in uncut
    assert '--local' in uncut
    wolves = (REPO_ROOT / "scripts" / "rebuild-wolves.sh").read_text()
    assert "LOCAL_OPT" in wolves


# --------------------------------------------------------------------------
# The new farm.py machinery, offline: kubectl and systemd-run are mocked.


class _FakeKubectl:
    """Answers kubectl calls from a script: {args-prefix: (rc, stdout, stderr)}."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, *a, **k):
        return self

    def run(self, args, **k):
        import subprocess
        self.calls.append(args)
        for prefix, (rc, out, err) in self.answers:
            if args[: len(prefix)] == prefix:
                return subprocess.CompletedProcess(args, rc, out, err)
        raise AssertionError(f"unexpected kubectl call: {args}")


def _node_doc(*, exo0="True", ghost="True"):
    def node(name, ready):
        return {"metadata": {"name": name},
                "status": {"conditions": [{"type": "Ready", "status": ready,
                                           "reason": "KubeletReady"}]}}
    import json
    return json.dumps({"items": [node("exo-0", exo0), node("ghost", ghost)]})


def test_cluster_available_requires_a_ready_node(monkeypatch):
    """The 03:08Z lesson's other half: an API that answers is not a cluster
    that can run a pod. The node probe is what reports WHY."""
    monkeypatch.setattr(farm.shutil, "which", lambda _: "/usr/bin/kubectl")
    kc = _FakeKubectl([
        (["-n", "argo", "get", "sa", "argo"], (0, "argo", "")),
        (["get", "nodes"], (0, _node_doc(exo0="False", ghost="False"), "")),
    ])
    monkeypatch.setattr(farm, "Kubectl", kc)
    ok, why = farm.cluster_available()
    assert not ok
    assert "no Ready node" in why and "exo-0" in why and "ghost" in why


def test_cluster_available_when_any_node_is_ready(monkeypatch):
    """Both nodes are the farm: exo-0 down must not idle a Ready ghost."""
    monkeypatch.setattr(farm.shutil, "which", lambda _: "/usr/bin/kubectl")
    kc = _FakeKubectl([
        (["-n", "argo", "get", "sa", "argo"], (0, "argo", "")),
        (["get", "nodes"], (0, _node_doc(exo0="False", ghost="True"), "")),
    ])
    monkeypatch.setattr(farm, "Kubectl", kc)
    ok, why = farm.cluster_available()
    assert ok and why == ""


def test_cluster_available_reports_a_failed_node_listing(monkeypatch):
    monkeypatch.setattr(farm.shutil, "which", lambda _: "/usr/bin/kubectl")
    kc = _FakeKubectl([
        (["-n", "argo", "get", "sa", "argo"], (0, "argo", "")),
        (["get", "nodes"], (1, "", "forbidden: nodes")),
    ])
    monkeypatch.setattr(farm, "Kubectl", kc)
    ok, why = farm.cluster_available()
    assert not ok and "nodes" in why


def test_run_capped_local_rejects_local_ffmpeg():
    with pytest.raises(farm.FarmError, match="prohibited"):
        farm.run_capped_local(["ffmpeg", "-i", "in.mp4", "out.mp4"],
                              reason="the test asked for local")


def test_run_capped_local_never_invokes_subprocess():
    with pytest.raises(farm.FarmError, match="prohibited"):
        farm.run_capped_local(["ffmpeg", "x"], reason="why")


def test_run_encode_farms_when_the_cluster_answers(monkeypatch):
    farmed = []
    monkeypatch.setattr(farm, "cluster_available", lambda *a, **k: (True, ""))
    monkeypatch.setattr(farm, "run_ffmpeg_on_cluster",
                        lambda argv, **kw: farmed.append(argv))
    where = farm.run_encode(["ffmpeg", "-i", "a", "b"], inputs=["a"], out="b")
    assert where == "cluster" and farmed


def test_run_encode_rejects_unreachable_cluster(monkeypatch):
    monkeypatch.setattr(farm, "cluster_available",
                        lambda *a, **k: (False, "kubectl not on PATH"))
    with pytest.raises(farm.FarmError, match="kubectl not on PATH"):
        farm.run_encode(["ffmpeg", "-i", "a", "b"], inputs=["a"], out="b")


def test_run_encode_does_not_retry_locally_when_the_farm_fails(monkeypatch):
    def boom(argv, **kw):
        raise farm.FarmError("pod cannot run: unschedulable")
    monkeypatch.setattr(farm, "cluster_available", lambda *a, **k: (True, ""))
    monkeypatch.setattr(farm, "run_ffmpeg_on_cluster", boom)
    with pytest.raises(farm.FarmError, match="unschedulable"):
        farm.run_encode(["ffmpeg", "-i", "a", "b"], inputs=["a"], out="b")


def test_run_encode_local_flag_never_probes_the_cluster(monkeypatch):
    monkeypatch.setattr(farm, "cluster_available",
                        lambda *a, **k: pytest.fail("probed under --local"))
    with pytest.raises(farm.FarmError, match="prohibited"):
        farm.run_encode(["ffmpeg", "x"], inputs=[], out="o", local=True)


# --- the chain runner: render.py's clips -> concat shape, rewritten --------


def _capture_chain(monkeypatch):
    captured = {}

    def fake_execute(*, name, script, uploads, out_rel, out, **kw):
        captured.update(name=name, script=script, uploads=uploads,
                        out_rel=out_rel)
    monkeypatch.setattr(farm, "_execute_on_cluster", fake_execute)
    monkeypatch.setattr(farm, "_verify_fetched", lambda *a, **k: {})
    return captured


def test_chain_rewrites_intermediates_and_the_concat_list(tmp_path,
                                                          monkeypatch):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"x")
    tmp = tmp_path / "scratch"
    tmp.mkdir()
    clip = tmp / "clip_001.mkv"
    out = tmp_path / "out.mp4"
    list_path = tmp / "concat_list.txt"
    argvs = [
        ["ffmpeg", "-i", str(src), "-c:v", "libx264", str(clip)],
        ["ffmpeg", "-f", "concat", "-i", str(list_path), str(out)],
    ]
    content = f"file '{clip}'\n"
    captured = _capture_chain(monkeypatch)
    farm.run_ffmpeg_chain_on_cluster(
        argvs, inputs=[src], out=out, tmp_prefix=tmp,
        text_files={list_path: content})
    script = captured["script"]
    # The clip is written and read POD-SIDE; only the output is fetched.
    assert f"{farm.WORK_DIR}/chain/clip_001.mkv" in script
    assert str(tmp) not in script
    # The concat list's CONTENT was rewritten to the pod's paths, and
    # travels base64 so a quoted path cannot become two tokens.
    import base64
    encoded = base64.b64encode(
        content.replace(str(tmp), f"{farm.WORK_DIR}/chain")
        .encode()).decode()
    assert encoded in script
    assert captured["out_rel"] == f"out/{out.name}"


def test_chain_rejects_a_last_command_that_does_not_write_the_output(
        tmp_path, monkeypatch):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"x")
    _capture_chain(monkeypatch)
    with pytest.raises(farm.FarmError, match="never writes"):
        farm.run_ffmpeg_chain_on_cluster(
            [["ffmpeg", "-i", str(src), str(tmp_path / "other.mp4")]],
            inputs=[src], out=tmp_path / "out.mp4")


def test_chain_rejects_a_staged_input_nothing_reads(tmp_path, monkeypatch):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"x")
    unread = tmp_path / "unread.mp4"
    unread.write_bytes(b"x")
    out = tmp_path / "out.mp4"
    _capture_chain(monkeypatch)
    with pytest.raises(farm.FarmError, match="never read"):
        farm.run_ffmpeg_chain_on_cluster(
            [["ffmpeg", "-i", str(src), str(out)]], inputs=[src, unread],
            out=out)
