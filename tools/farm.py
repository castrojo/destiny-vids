#!/usr/bin/env python3
"""Offload a long encode to the ghost k3s cluster so the laptop stays usable.

The laptop's 16 threads are shared with every agent session on it; the ghost
cluster is ~99% idle. This tool takes one input file and an ffmpeg encode
recipe, ships both to a pod on ``ghost``, streams progress back, fetches the
result, and verifies it against the source (or a ``--reference`` encode).

    python3 tools/farm.py ~/Videos/Wolves/Prod/01-intro.mp4 \
        --out renders/01-intro.crf18.mp4
    python3 tools/farm.py in.mp4 --out out.mp4 --segments 6 \
        --audio-args "-c:a aac -b:a 192k" -- \
        -c:v libx264 -crf 20 -preset medium

THE UNIT OF PARALLELISM is one input file split into N time-range *segments*:
each segment is re-encoded independently and the pieces are joined with
``-c copy`` (the megacut's own trick). Two reasons, one measured and one
structural:

1. x264 scales sublinearly past ~8 threads, so 4 processes at 6 threads each
   (``--threads``) encode the same film considerably faster than 1 process at
   24 threads. Segmenting gets that parallelism out of a single input file;
   a whole-act render and a megacut segment are the same job here.
2. The boundary must be free of caller bookkeeping: segments are cut on the
   frame grid (start/duration are exact multiples of the frame period), every
   chunk is encoded from scratch so each starts with an IDR, and the join
   never re-encodes. ``verify_output`` then *proves* the seam arithmetic:
   duration within 0.5s and, when both sides report it, an exact frame-count
   match. An exit code of 0 alone is not evidence (issue #88 shipped a file
   8.5s short), so verification compares against the source by default and
   against a locally-encoded ``--reference`` for stream shape.

DATA MOVEMENT IS kubectl cp, deliberately: the cluster has no artifact
repository (the lab rejects MinIO/S3) and no shared filesystem (local-path,
ReadWriteOnce). The pod mounts one PVC, waits for a ready-marker, encodes,
waits for a fetched-marker, and exits; the tool orchestrates those markers
and streams ``kubectl logs`` so a 20-minute encode is not a silent wait.

THE IMAGE is ``lscr.io/linuxserver/ffmpeg`` (8.1.2), a full non-free build
(libx264/libx265/libfdk_aac — and Mesa's VAAPI drivers, unused here: on 24
cores libx264 measured FASTER than h264_vaapi on identical input, 15.7x vs
13.7x realtime, at better quality; CPU-only is both the quality and the
speed choice). The researched default, ``ghcr.io/jrottenberg/ffmpeg``, cannot
be pulled by this cluster: pulls go through the zot registry mirror whose
on-demand sync only fires on *tag* references (lab ADR 0007), ghcr's
jrottenberg repo no longer publishes any tag past 6.0, and the sync allowlist
covers neither ``jrottenberg/*`` on ghcr nor on docker.io. Widening that
allowlist is a ``lab/`` change and out of scope here; ``lscr.io`` is
allowlisted wholesale and linuxserver/ffmpeg is the same class of full build.

DEGRADE, NEVER BLOCK: if the cluster is unreachable the tool says so once and
runs the same segmented encode locally with ``tools.render.find_ffmpeg``.
``--local`` forces that path; ``--keep`` leaves the Workflow and PVC for
debugging; ``--dry-run`` prints the plan and manifest and does nothing.

BOTH NODES ARE THE FARM. Nothing is pinned by default: exo-0 and ghost each
have 32 allocatable cores, neither is tainted, and BOTH carry the ffmpeg image
(verified by running it on ghost — it resolved in 3.6 s). Pinning to exo-0 left
half the cluster idle while a segment queued. One Workflow and one PVC per
segment means segments are independent, so the scheduler spreads them; ``--node``
still pins when a run has to land somewhere specific.

RESOURCE SHAPE follows the house rule: requests gate SCHEDULING, limits gate
BURST, and the cluster runs at 156–263% limit overcommit. The pod requests a
schedulable 2 CPU / 4 Gi — low enough to land on either node — and may burst to
``--limit-cpu`` 24 / ``--limit-memory`` 16 Gi — requesting 24
gets you Pending; requesting 2 with a limit of 24 measures 24 cores (nproc)
inside the pod.

TWO ENTRY POINTS share the machinery: the CLI above (one file, chunked
internally) and ``run_ffmpeg_on_cluster`` — one caller-supplied ffmpeg argv
run verbatim in a pod, with its local input paths staged by kubectl cp and
rewritten to the pod's view (``rewrite_argv_for_pod``). megacut's ENCODE
segments are the first caller of the second; remote is the default whenever
the cluster is reachable, per the owner's ruling, and local is the stated
fallback, never the silent one.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import shutil
import string
import subprocess
import sys
import tempfile
import threading
import time
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.render import find_ffmpeg, find_ffprobe  # noqa: E402

# See the module docstring for why this is linuxserver and not jrottenberg.
DEFAULT_IMAGE = "lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76"
DEFAULT_NAMESPACE = "argo"
DEFAULT_SERVICE_ACCOUNT = "argo"
# None = let the scheduler choose. exo-0 and ghost are 32 cores each, both
# untainted, both holding the image; pinning halves the farm. `--node` pins.
DEFAULT_NODE = None
DEFAULT_CPU = "2"               # request: low, so it always schedules
DEFAULT_LIMIT_CPU = "24"        # limit: the burst ceiling on idle exo-0
DEFAULT_MEMORY = "4Gi"          # request
DEFAULT_LIMIT_MEMORY = "16Gi"   # limit
DEFAULT_THREADS = 6
DEFAULT_TIMEOUT = 7200          # matches the controller's activeDeadlineSeconds
WORK_DIR = "/work"
LABELS = {"app.kubernetes.io/part-of": "destiny-vids-farm"}

# Delivery-grade default: spend the cluster's CPU on picture quality, and never
# touch the audio — a copy is zero generations lost, which the audio tenet
# requires. The video recipe follows ``--``; audio is a separate single pass
# (see build_plan) controlled by --audio-args.
DEFAULT_VIDEO_ARGS = ["-c:v", "libx264", "-crf", "18", "-preset", "slow"]
DEFAULT_AUDIO_ARGS = ["-c:a", "copy"]

# A duration mismatch is a real bug (issue #88 was 8.5s short); seam drift from
# audio frame granularity is tens of milliseconds. Half a second sits cleanly
# between the two.
SEAM_TOLERANCE_S = 0.5

# Named so a test can point it somewhere that does not exist (megacut's
# LINUXBREW_FFMPEG pattern): the NATIVE ffprobe on an atomic Fedora/Bluefin
# host, beside the full linuxbrew ffmpeg.
LINUXBREW_FFPROBE = "/home/linuxbrew/.linuxbrew/bin/ffprobe"


def native_ffprobe():
    """An ffprobe that can see the WHOLE local filesystem.

    ``find_ffprobe`` prefers the running ffmpeg CONTAINER on this host, and
    that container mounts only ``$HOME`` — a fetched output parked in a
    tempfile directory (``/var/tmp``, where megacut's segments live) is "No
    such file or directory" to it, which reads exactly like a failed
    download. Verification of a LOCAL file the caller placed anywhere wants a
    native probe: ``DESTINY_FFPROBE``, the binary beside ``DESTINY_FFMPEG``,
    the linuxbrew build, and only then the container resolver (fine whenever
    the output lives under ``$HOME``, as the farm CLI's does).
    """
    override = os.environ.get("DESTINY_FFPROBE")
    if override:
        return shlex.split(override)
    ffmpeg_override = os.environ.get("DESTINY_FFMPEG")
    if ffmpeg_override:
        head, sep, tail = shlex.split(ffmpeg_override)[0].rpartition("ffmpeg")
        if sep and Path(f"{head}ffprobe{tail}").exists():
            return [f"{head}ffprobe{tail}"]
    if Path(LINUXBREW_FFPROBE).exists():
        return [LINUXBREW_FFPROBE]
    return find_ffprobe()


class FarmError(RuntimeError):
    """A farm failure with a message worth printing verbatim."""


# --------------------------------------------------------------------------
# Probing (always local: the source and the output both live on the laptop)


def probe(path, ffprobe):
    """The facts the plan and the verifier need about one media file.

    Duration comes from the VIDEO stream where possible — the same lesson
    social.py learned: a format-level duration can be the longest stream,
    which is the wrong number when audio outruns the picture.
    """
    cmd = [*ffprobe, "-v", "error", "-print_format", "json",
           "-show_entries",
           "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,"
           "avg_frame_rate,duration,nb_frames:format=duration",
           # rendering.md: the resolved ffprobe is usually a container exec,
           # which does not inherit this process's working directory.
           str(Path(path).resolve())]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FarmError(f"ffprobe cannot read {path}: {proc.stderr.strip()[:200]}")
    out = proc.stdout
    doc = json.loads(out)
    streams = doc.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise FarmError(f"no video stream in {path}")
    fps = Fraction(video.get("r_frame_rate") or "0/1")
    duration = float(video.get("duration") or doc["format"]["duration"])
    nb = video.get("nb_frames")
    return {
        "duration": duration,
        "fps": fps,
        "vfr": _is_vfr(video),
        "frame_count": int(nb) if nb and nb != "N/A" else None,
        "codec_name": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "pix_fmt": video.get("pix_fmt"),
        "stream_kinds": [s.get("codec_type") for s in streams],
    }


def _is_vfr(video):
    r, a = video.get("r_frame_rate"), video.get("avg_frame_rate")
    if not r or not a:
        return False
    try:
        rf, af = Fraction(r), Fraction(a)
    except (ValueError, ZeroDivisionError):
        return False
    return rf > 0 and af > 0 and abs(rf - af) / rf > Fraction(1, 100)


# --------------------------------------------------------------------------
# The plan: pure functions, no I/O. This is the part tests pin down.


def chunk_boundaries(facts, segments):
    """[(start_s, dur_s, n_frames)] on the frame grid, covering the file
    exactly. ``n_frames`` is None for a VFR source (no frame grid exists).

    Frame-grid boundaries are what make the seam safe, but only if the chunk
    length is expressed in FRAMES: a float ``-t`` duration is converted to the
    stream's int64 timebase and truncates, which drops the boundary frame
    whenever the float lands a hair low (measured: act VI lost exactly one
    frame per seam, 13297 vs 13301). ``-ss`` for the start (accurate seek is
    exact at nanosecond formatting) plus ``-frames:v N`` for the length is
    integer-exact. VFR sources fall back to ``-t`` time slices and lean on
    verification to catch a bad seam.
    """
    segments = max(1, segments)
    duration, fps = facts["duration"], facts["fps"]
    if facts["vfr"] or fps <= 0:
        step = duration / segments
        return [(i * step, step, None) for i in range(segments)]
    frames = facts["frame_count"] or round(duration * float(fps))
    segments = max(1, min(segments, frames))
    bounds = [round(i * frames / segments) for i in range(segments + 1)]
    return [(float(Fraction(b0) / fps), float(Fraction(b1 - b0) / fps),
             b1 - b0)
            for b0, b1 in zip(bounds, bounds[1:])]


def _chunk_out_name(out_name, i):
    return f"chunk_{i:04d}.mp4"


def build_plan(*, facts, out_name, segments, video_args, audio_args, threads,
               work_dir, src_arg, ffmpeg=("ffmpeg",)):
    """The whole encode: one argv per chunk, one audio pass, one join argv.

    Audio is NOT segmented with the video. A per-chunk audio copy leaves AAC
    priming/edit-list seams that the join can only clamp ("Non-monotonic DTS"
    warnings, and a real timestamp wobble per seam). Instead the chunks are
    video-only (``-an``), one continuous audio pass runs alongside them, and
    the join muxes the two — zero audio seams, at most one generation, and
    zero generations with the default ``-c:a copy``.

    ``src_arg`` is the input path *as the executor sees it* — a PVC path for
    the farm, the local absolute path for local mode. Pure: no I/O, so tests
    drive it with fabricated facts.
    """
    spans = chunk_boundaries(facts, segments)
    chunks = []
    for i, (ss, dur, nframes) in enumerate(spans):
        argv = [*ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "warning",
                # Input-side seek: frame-accurate in ffmpeg >= 5 (it decodes
                # and discards), and rebases timestamps to zero, which is
                # exactly what a chunk needs. The rendering.md objection to
                # input seeking is about frame PHASE across a 29.97->30
                # conversion; this tool never changes frame rate.
                "-ss", f"{ss:.9f}", "-i", src_arg]
        if nframes is not None:
            # Integer frame count: exact. A float -t truncates into the
            # stream timebase and eats the seam frame (see chunk_boundaries).
            argv += ["-frames:v", str(nframes)]
        else:
            argv += ["-t", f"{dur:.6f}"]
        argv += [*video_args, "-an",
                # After the recipe so the farm's threading wins even when the
                # recipe carries its own -threads (documented, not a bug).
                "-threads", str(threads),
                "-progress", f"{work_dir}/logs/{_chunk_out_name(out_name, i)}.progress",
                "-y", f"{work_dir}/chunks/{_chunk_out_name(out_name, i)}"]
        chunks.append({"index": i, "ss": ss, "dur": dur, "argv": argv})
    concat_list = [f"{work_dir}/chunks/{_chunk_out_name(out_name, i)}"
                   for i in range(len(chunks))]

    has_audio = "audio" in facts["stream_kinds"]
    audio = None
    if has_audio:
        # Matroska because it holds any codec without MP4 edit lists; the join
        # stream-copies it into the final container.
        audio = [*ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "warning",
                 "-i", src_arg, *audio_args, "-vn",
                 "-y", f"{work_dir}/out/audio.mkv"]

    join = [*ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "warning",
            "-f", "concat", "-safe", "0", "-i", f"{work_dir}/concat.txt"]
    if audio:
        join += ["-i", f"{work_dir}/out/audio.mkv",
                 "-map", "0:v:0", "-map", "1:a:0"]
    join += ["-c", "copy"]
    if out_name.lower().endswith(".mp4"):
        join += ["-movflags", "+faststart"]
    join += ["-y", f"{work_dir}/out/{out_name}"]
    return {"chunks": chunks, "audio": audio, "concat_list": concat_list,
            "join": join, "out_rel": f"out/{out_name}",
            "total_duration": facts["duration"]}


def pod_script(plan):
    """The bash the pod runs. Waits for input, encodes chunks in parallel,
    prints a progress line every 15s, joins, and waits to be harvested.

    The ready/fetched markers are the poor man's artifact repository: Argo has
    no artifact store here, so the pod idles on files the caller creates with
    kubectl exec around the two kubectl cp transfers.
    """
    chunk_lines = []
    exit_files = []
    for c in plan["chunks"]:
        # The log/exit file names derive from the progress path so the three
        # never disagree.
        log = c["argv"][c["argv"].index("-progress") + 1][:-len(".progress")] + ".log"
        exitf = log[:-len(".log")] + ".exit"
        exit_files.append(exitf)
        chunk_lines.append(
            f"( {shlex.join(c['argv'])} > {shlex.quote(log)} 2>&1; "
            f"echo $? > {shlex.quote(exitf)} ) &\npids+=($!)")
    if plan["audio"]:
        log = f"{WORK_DIR}/logs/audio.log"
        exit_files.append(log[:-len(".log")] + ".exit")
        chunk_lines.append(
            f"( {shlex.join(plan['audio'])} > {shlex.quote(log)} 2>&1; "
            f"echo $? > {shlex.quote(log[:-len('.log')] + '.exit')} ) &\npids+=($!)")
    concat_body = "\n".join(f"file '{p}'" for p in plan["concat_list"])
    exits = " ".join(shlex.quote(e) for e in exit_files)
    n = len(plan["chunks"])
    return f"""#!/bin/bash
set -uo pipefail
export LC_ALL=C
cd {WORK_DIR} || {{ echo "no {WORK_DIR} mounted"; exit 1; }}
mkdir -p in chunks logs out
say() {{ printf '%s [farm] %s\\n' "$(date +%H:%M:%S)" "$*"; }}
say "pod up on $(hostname); {n} chunks of {plan['total_duration']:.1f}s; waiting for input"
while [ ! -f in/.ready ]; do sleep 2; done
say "input arrived:"; ls -l in/
cat > concat.txt <<'CONCAT'
{concat_body}
CONCAT
pids=()
{chr(10).join(chunk_lines)}
(
  while true; do
    [ -f .chunks_done ] && break
    s=$(awk -F= '$1=="out_time_us"{{v[FILENAME]=$2}} END{{t=0; for(f in v) t+=v[f]; printf "%.1f", t/1000000}}' logs/chunk_*.progress 2>/dev/null)
    say "encoded ${{s:-0.0}}s of {plan['total_duration']:.1f}s"
    sleep 15
  done
) &
mon=$!
wait "${{pids[@]}}"
touch .chunks_done
kill "$mon" 2>/dev/null
fail=0
for exitf in {exits}; do
  rc=$(cat "$exitf" 2>/dev/null)
  if [ "$rc" != "0" ]; then
    fail=1
    say "job FAILED (rc=${{rc:-missing}}): $exitf"
    tail -n 8 "${{exitf%.exit}}.log"
  fi
done
if [ "$fail" -ne 0 ]; then say "aborting: chunk failures"; exit 1; fi
say "joining {n} chunks"
if ! {shlex.join(plan["join"])}; then say "join FAILED"; exit 1; fi
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 {shlex.quote(plan['out_rel'])} 2>/dev/null)
printf '{{"output":%s,"duration":%s}}\\n' '"{plan["out_rel"]}"' '"${{dur:-null}}"' > out/.done.json
say "encoded {plan['out_rel']} duration=${{dur:-?}}s; waiting for fetch"
while [ ! -f .fetched ]; do sleep 2; done
say "output fetched; pod done"
"""


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:40] or "encode"


def farm_name(src_name):
    rand = "".join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(4))
    return f"farm-{slugify(Path(src_name).stem)}-{rand}"


def storage_for(src_bytes):
    """PVC size: source + chunks + output with headroom, min 1Gi."""
    return f"{max(1, -(-3 * src_bytes // (1024 ** 3)))}Gi"


def build_pvc(name, *, namespace, storage):
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {"name": name, "namespace": namespace, "labels": dict(LABELS)},
        "spec": {"accessModes": ["ReadWriteOnce"],
                 "storageClassName": "local-path",
                 "resources": {"requests": {"storage": storage}}},
    }


def build_workflow(name, script, *, namespace, image, cpu, limit_cpu, memory,
                   limit_memory, node, service_account, keep):
    """A plain Workflow — never a WorkflowTemplate, which would have to be
    GitOps'd from lab/ and ArgoCD would fight it."""
    spec = {
        "entrypoint": "encode",
        "serviceAccountName": service_account,
        "volumes": [{"name": "work",
                     "persistentVolumeClaim": {"claimName": name}}],
        "templates": [{
            "name": "encode",
            **({"nodeSelector": {"kubernetes.io/hostname": node}}
               if node else {}),
            "container": {
                "name": "main",
                "image": image,
                # The image's entrypoint is ffmpeg itself; command replaces it.
                "command": ["/bin/bash", "-c", script],
                "resources": {
                    # House style (156–263% limit overcommit): a LOW request
                    # always schedules; the HIGH limit is the real budget on
                    # an idle node.
                    "requests": {"cpu": cpu, "memory": memory},
                    "limits": {"cpu": limit_cpu, "memory": limit_memory},
                },
                "volumeMounts": [{"name": "work", "mountPath": WORK_DIR}],
            },
        }],
    }
    if not keep:
        # Backstop in case the tool dies between submit and cleanup. --keep
        # omits this so a debugging session is not reaped mid-look.
        spec["ttlStrategy"] = {"secondsAfterSuccess": 3600,
                               "secondsAfterFailure": 604800}
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": dict(LABELS),
            "annotations": {
                "description": "One encode fanned out over ghost by tools/farm.py "
                               "(destiny-vids): kubectl cp in, parallel libx264 "
                               "chunks on one PVC, concat -c copy, kubectl cp out.",
            },
        },
        "spec": spec,
    }


# --------------------------------------------------------------------------
# kubectl plumbing


class Kubectl:
    def __init__(self, kubeconfig=None, namespace=DEFAULT_NAMESPACE):
        self.base = ["kubectl"]
        if kubeconfig:
            self.base += ["--kubeconfig", str(kubeconfig)]
        self.namespace = namespace

    def run(self, args, timeout=60, check=True, input_text=None):
        proc = subprocess.run(self.base + args, capture_output=True, text=True,
                              timeout=timeout, input=input_text)
        if check and proc.returncode != 0:
            raise FarmError(
                f"kubectl {args[0]} failed:\n{proc.stderr.strip()[:800]}")
        return proc

    def apply_json(self, doc):
        return self.run(["apply", "-f", "-"], input_text=json.dumps(doc))

    def exec(self, pod, argv, check=True):
        return self.run(["-n", self.namespace, "exec", pod, "-c", "main",
                         "--", *argv], check=check)

    def cp(self, src, dst):
        # -c main: the argo wait container matches kubectl's default pick on
        # some versions, and it has no tar.
        return self.run(["cp", str(src), dst, "-c", "main"], timeout=3600)

    def workflow_phase(self, name):
        proc = self.run(["-n", self.namespace, "get", "workflow", name,
                         "-o", "jsonpath={.status.phase}"], check=False)
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def pod_for(self, workflow):
        proc = self.run(["-n", self.namespace, "get", "pods", "-l",
                         f"workflows.argoproj.io/workflow={workflow}",
                         "-o", "jsonpath={.items[0].metadata.name}"],
                        check=False)
        return proc.stdout.strip()

    def pod_status(self, pod):
        proc = self.run(["-n", self.namespace, "get", "pod", pod, "-o",
                         "json"], check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None

    def delete(self, kind, name):
        self.run(["-n", self.namespace, "delete", kind, name, "--wait=false"],
                 check=False)


def pod_blocker(status):
    """None once the main container runs; otherwise the reason it can't.

    Turns the two slow failure modes — an unschedulable request and a bad
    image — into immediate, legible errors instead of a two-hour wait.
    """
    if not status:
        return "pod object not found yet"
    conds = {c.get("type"): c for c in status["status"].get("conditions", [])}
    sched = conds.get("PodScheduled", {})
    if sched.get("status") == "False" and sched.get("reason") == "Unschedulable":
        return (f"unschedulable: {sched.get('message', '').strip()} "
                f"— lower --cpu/--memory")
    for cs in status["status"].get("containerStatuses", []):
        if cs.get("name") != "main":
            continue
        state = cs.get("state", {})
        if "running" in state:
            return None
        waiting = state.get("waiting", {})
        if waiting.get("reason") in ("ErrImagePull", "ImagePullBackOff",
                                     "CreateContainerError",
                                     "CrashLoopBackOff"):
            return (f"container cannot start: {waiting.get('reason')}: "
                    f"{waiting.get('message', '').strip()[:200]}")
    return "pending"


def cluster_available(kubeconfig=None, namespace=DEFAULT_NAMESPACE):
    """(ok, why_not). Strict timeouts: the offline suite must not hang."""
    if shutil.which("kubectl") is None:
        return False, "kubectl not on PATH"
    kc = Kubectl(kubeconfig, namespace)
    try:
        proc = kc.run(["-n", namespace, "get", "sa", DEFAULT_SERVICE_ACCOUNT,
                       "--request-timeout=8s"], timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"kubectl cannot reach the API server ({exc})"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return False, tail[-1] if tail else "kubectl get sa failed"
    return True, ""


def _stream_logs(kc, pod, prefix="  "):
    """Copy the pod's main-container log to stdout until the container exits."""
    proc = subprocess.Popen(
        kc.base + ["-n", kc.namespace, "logs", "-f", "--tail=-1", "-c", "main", pod],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        errors="replace")
    for line in proc.stdout:
        print(f"{prefix}{line}", end="", flush=True)
    proc.wait()


def _tail_log(kc, pod):
    proc = kc.run(["-n", kc.namespace, "logs", pod, "-c", "main", "--tail=30"],
                  check=False)
    if proc.stdout.strip():
        print("---- last pod log lines ----")
        print(proc.stdout.strip())


# --------------------------------------------------------------------------
# Executors


def _execute_on_cluster(*, name, script, uploads, out_rel, out, kc, image,
                        cpu, limit_cpu, memory, limit_memory, node,
                        service_account, storage, keep, timeout, desc,
                        label="farm", log_prefix="  "):
    """The generic pod lifecycle: submit, stage, wait, fetch, clean up.

    ``uploads`` is [(local_path, work_dir-relative staging path)]; every file
    lands before the ``in/.ready`` marker is touched. ``out_rel`` is the
    work_dir-relative result the pod's ``out/.done.json`` vouches for, fetched
    to the local ``out``. This is the machinery both the chunked single-file
    CLI (``run_on_cluster``) and the one-argv capability
    (``run_ffmpeg_on_cluster``) share — the differences are all in the script
    and the upload list, not here.
    """
    deadline = time.monotonic() + timeout
    kc.apply_json(build_pvc(name, namespace=kc.namespace, storage=storage))
    kc.apply_json(build_workflow(name, script, namespace=kc.namespace,
                                 image=image, cpu=cpu, limit_cpu=limit_cpu,
                                 memory=memory, limit_memory=limit_memory,
                                 node=node,
                                 service_account=service_account, keep=keep))
    print(f"{label}: workflow {name} submitted (node {node}, {desc})")
    try:
        pod = ""
        while time.monotonic() < deadline:
            pod = kc.pod_for(name)
            if pod:
                break
            time.sleep(2)
        if not pod:
            raise FarmError("no pod appeared for the workflow")

        print(f"{label}: waiting for the pod (image pull on first run "
              f"~5 min)…")
        blocker = "pending"
        while time.monotonic() < deadline:
            blocker = pod_blocker(kc.pod_status(pod))
            if blocker is None:
                break
            if blocker != "pending" and blocker != "pod object not found yet":
                _tail_log(kc, pod)
                raise FarmError(f"pod cannot run: {blocker}")
            time.sleep(3)
        else:
            _tail_log(kc, pod)
            raise FarmError(f"pod never became Ready (last state: {blocker})")

        logs = threading.Thread(target=_stream_logs, args=(kc, pod, log_prefix),
                                daemon=True)
        logs.start()

        for local, rel in uploads:
            size = Path(local).stat().st_size
            print(f"{label}: uploading {size / (1024 ** 2):.1f} MiB "
                  f"({Path(local).name}) …", flush=True)
            t0 = time.monotonic()
            kc.cp(local, f"{kc.namespace}/{pod}:{WORK_DIR}/{rel}")
            print(f"{label}: uploaded in {time.monotonic() - t0:.0f}s",
                  flush=True)
        kc.exec(pod, ["touch", f"{WORK_DIR}/in/.ready"])

        # Encode runs; poll for the completion marker the pod writes, watching
        # the workflow phase for failure in parallel.
        while time.monotonic() < deadline:
            phase = kc.workflow_phase(name)
            if phase in ("Failed", "Error"):
                logs.join(timeout=5)
                _tail_log(kc, pod)
                raise FarmError(f"workflow {phase}")
            done = kc.exec(pod, ["test", "-f", f"{WORK_DIR}/out/.done.json"],
                           check=False)
            if done.returncode == 0:
                break
            time.sleep(5)
        else:
            raise FarmError(f"encode exceeded --timeout {timeout}s")

        Path(out).parent.mkdir(parents=True, exist_ok=True)
        t0 = time.monotonic()
        kc.cp(f"{kc.namespace}/{pod}:{WORK_DIR}/{out_rel}", str(out))
        print(f"{label}: downloaded {out_rel} in "
              f"{time.monotonic() - t0:.0f}s", flush=True)
        kc.exec(pod, ["touch", f"{WORK_DIR}/.fetched"], check=False)

        ok_deadline = time.monotonic() + 120
        while time.monotonic() < ok_deadline:
            if kc.workflow_phase(name) == "Succeeded":
                break
            time.sleep(3)
        else:
            raise FarmError("pod did not exit after fetch; inspect with --keep")
        logs.join(timeout=10)
    finally:
        if keep:
            print(f"{label}: --keep — workflow {name} and PVC {name} left in "
                  f"namespace {kc.namespace}; delete both when done")
        else:
            kc.delete("workflow", name)
            kc.delete("pvc", name)
    return 0


def run_on_cluster(plan, *, name, src, out, script, kc, image, cpu, limit_cpu,
                   memory, limit_memory, node, service_account, storage, keep,
                   timeout):
    return _execute_on_cluster(
        name=name, script=script,
        uploads=[(src, f"in/{Path(src).name}")],
        out_rel=plan["out_rel"], out=out, kc=kc, image=image, cpu=cpu,
        limit_cpu=limit_cpu, memory=memory, limit_memory=limit_memory,
        node=node, service_account=service_account, storage=storage,
        keep=keep, timeout=timeout,
        desc=f"{len(plan['chunks'])} chunks x up to {limit_cpu} cpu")


# --------------------------------------------------------------------------
# The generic capability: ONE ffmpeg invocation, run on the cluster.
#
# megacut's ENCODE segments are the first caller: each is a single argv over
# one or two local inputs, and each is big enough (minutes of 1080p60 at
# crf 16 preset slow) to be worth shipping. The chunked path above re-segments
# one file internally; this path runs the caller's argv VERBATIM — the caller
# owns the recipe, the farm owns the data movement and the proof.


def rewrite_argv_for_pod(argv, inputs, out, *, work_dir=WORK_DIR):
    """Map a LOCAL ffmpeg argv onto the pod's filesystem view.

    ``argv[0]`` — the local ffmpeg binary, e.g. the linuxbrew build this host
    needs for H.264 — becomes plain ``ffmpeg``; the farm image carries a full
    non-free build on PATH, so the recipe travels, not the binary. Every
    token that IS one of ``inputs`` is staged at ``{work_dir}/in/NN-name``
    (the ordinal prefix keeps two same-named inputs distinct) and rewritten
    there; the one token that IS ``out`` is rewritten to
    ``{work_dir}/out/<name>``.

    Matching is exact-token only, by design: a path embedded inside a filter
    string would NOT be rewritten, so a caller whose argv works that way is
    rejected loudly below rather than silently running against a missing pod
    file. megacut's chains carry no paths inside filters.

    Returns (pod_argv, uploads, pod_out) with uploads as
    [(local_Path, work_dir-relative staging path)].
    """
    inputs = [Path(p) for p in inputs]
    staged = {}
    uploads = []
    for i, p in enumerate(inputs):
        rel = f"in/{i:02d}-{p.name}"
        staged[str(p)] = f"{work_dir}/{rel}"
        uploads.append((p, rel))
    out_name = Path(out).name  # basename only inside the pod
    pod_out = f"{work_dir}/out/{out_name}"
    out_str = str(out)

    seen_inputs = set()
    seen_out = False
    pod_argv = ["ffmpeg"]
    for tok in argv[1:]:
        if tok in staged:
            pod_argv.append(staged[tok])
            seen_inputs.add(tok)
        elif tok == out_str:
            pod_argv.append(pod_out)
            seen_out = True
        else:
            pod_argv.append(tok)
    missing = [str(p) for p in inputs if str(p) not in seen_inputs]
    if missing:
        raise FarmError(f"argv never reads staged input(s) {missing} — the "
                        f"input list and the argv disagree")
    if not seen_out:
        raise FarmError(f"argv never writes {out_str} — nothing to fetch "
                        f"back; the output path must appear verbatim")
    return pod_argv, uploads, pod_out


def pod_script_run(pod_argv, out_rel, *, work_dir=WORK_DIR):
    """The bash for ONE caller-supplied ffmpeg invocation.

    Same marker protocol as the chunked script — wait for staged input, run,
    leave a probed ``out/.done.json``, wait to be harvested — because
    ``_execute_on_cluster`` orchestrates both. A non-zero exit tails the job
    log into the pod log, which is what the caller streams.
    """
    return f"""#!/bin/bash
set -uo pipefail
export LC_ALL=C
cd {work_dir} || {{ echo "no {work_dir} mounted"; exit 1; }}
mkdir -p in logs out
say() {{ printf '%s [farm] %s\\n' "$(date +%H:%M:%S)" "$*"; }}
say "pod up on $(hostname); waiting for input"
while [ ! -f in/.ready ]; do sleep 2; done
say "input arrived:"; ls -l in/
say {shlex.quote("running: " + shlex.join(pod_argv))}
if ! {shlex.join(pod_argv)} > logs/job.log 2>&1; then
  rc=$?
  say "job FAILED (rc=$rc)"
  tail -n 20 logs/job.log
  exit 1
fi
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 {shlex.quote(out_rel)} 2>/dev/null)
printf '{{"output":%s,"duration":%s}}\\n' '"{out_rel}"' '"${{dur:-null}}"' > out/.done.json
say "encoded {out_rel} duration=${{dur:-?}}s; waiting for fetch"
while [ ! -f .fetched ]; do sleep 2; done
say "output fetched; pod done"
"""


def run_ffmpeg_on_cluster(argv, *, inputs, out, name=None, kc=None,
                          kubeconfig=None, namespace=DEFAULT_NAMESPACE,
                          image=DEFAULT_IMAGE, cpu=DEFAULT_CPU,
                          limit_cpu=DEFAULT_LIMIT_CPU, memory=DEFAULT_MEMORY,
                          limit_memory=DEFAULT_LIMIT_MEMORY, node=DEFAULT_NODE,
                          service_account=DEFAULT_SERVICE_ACCOUNT, keep=False,
                          timeout=DEFAULT_TIMEOUT, expected_duration=None,
                          label=None, ffprobe=None):
    """Run ONE local ffmpeg argv on the cluster and fetch its output back.

    The argv is the caller's recipe verbatim — inputs staged by kubectl cp,
    paths rewritten to the pod's view (``rewrite_argv_for_pod``), output
    fetched to the local ``out``. The audio tenet is structural here: the
    SAME argv runs, so the sound takes exactly the generations the local run
    would — the only difference is whose CPUs do the work.

    Verification is the farm's own rule (exit 0 is not evidence, #88): the
    fetched file must ffprobe as media with a video stream, and when
    ``expected_duration`` is given its container duration must land within
    SEAM_TOLERANCE_S of it. Semantic checks (video extent vs the item's own
    clock) stay with the caller.
    """
    inputs = [Path(p) for p in inputs]
    out = Path(out)
    for p in inputs:
        if not p.exists():
            raise FarmError(f"input does not exist: {p}")
    name = name or farm_name(out.name)
    label = label or f"farm[{name}]"
    pod_argv, uploads, pod_out = rewrite_argv_for_pod(argv, inputs, out)
    out_rel = pod_out[len(WORK_DIR) + 1:]
    script = pod_script_run(pod_argv, out_rel)
    kc = kc or Kubectl(kubeconfig, namespace)
    total = sum(p.stat().st_size for p in inputs)
    _execute_on_cluster(
        name=name, script=script, uploads=uploads, out_rel=out_rel, out=out,
        kc=kc, image=image, cpu=cpu, limit_cpu=limit_cpu, memory=memory,
        limit_memory=limit_memory, node=node, service_account=service_account,
        storage=storage_for(total), keep=keep, timeout=timeout,
        desc=f"1 encode x up to {limit_cpu} cpu",
        label=label, log_prefix=f"  [{name}] ")
    try:
        facts = probe(out, ffprobe or native_ffprobe())
    except (FarmError, RuntimeError) as exc:
        raise FarmError(f"fetched output does not probe as media: {exc}")
    if expected_duration is not None:
        drift = facts["duration"] - float(expected_duration)
        if abs(drift) > SEAM_TOLERANCE_S:
            raise FarmError(
                f"output is {facts['duration']:.3f}s but the caller expected "
                f"{float(expected_duration):.3f}s — {drift:+.3f}s is a "
                f"re-time, not rounding (#88)")
    print(f"{label}: verify ok — {out.name} {facts['duration']:.3f}s "
          f"{facts['codec_name']} {facts['width']}x{facts['height']}")
    return facts


def _local_progress(plan, done):
    total = plan["total_duration"]
    logs = Path(plan["chunks"][0]["argv"][plan["chunks"][0]["argv"].index("-progress") + 1]).parent
    while not done.wait(15):
        seen = 0.0
        for prog in sorted(logs.glob("*.progress")):
            last = 0
            try:
                for line in prog.read_text(errors="replace").splitlines():
                    if line.startswith("out_time_us="):
                        v = line.split("=", 1)[1]
                        last = int(v) if v.isdigit() else last  # 'N/A' at t=0
            except OSError:
                continue
            seen += last / 1_000_000
        print(f"  [farm] encoded {seen:.1f}s of {total:.1f}s", flush=True)


def run_locally(plan, *, workers):
    """The same plan, run here. Used by --local and by the unreachable-cluster
    fallback — degrade to a slower encode, never to no encode."""
    from concurrent.futures import ThreadPoolExecutor

    for c in plan["chunks"]:
        prog = Path(c["argv"][c["argv"].index("-progress") + 1])
        prog.parent.mkdir(parents=True, exist_ok=True)
        Path(plan["concat_list"][0]).parent.mkdir(parents=True, exist_ok=True)
    Path(plan["join"][-1]).parent.mkdir(parents=True, exist_ok=True)
    Path(plan["join"][plan["join"].index("-i") + 1]).write_text(
        "".join(f"file '{p}'\n" for p in plan["concat_list"]))

    done = threading.Event()
    monitor = threading.Thread(target=_local_progress, args=(plan, done),
                               daemon=True)
    monitor.start()

    def log_for(argv, label):
        if "-progress" in argv:
            prog = argv[argv.index("-progress") + 1]
            return Path(prog[:-len(".progress")] + ".log")
        return Path(plan["concat_list"][0]).parent.parent / "logs" / f"{label}.log"

    jobs = [(f"chunk {c['index']}", c["argv"]) for c in plan["chunks"]]
    if plan["audio"]:
        jobs.append(("audio", plan["audio"]))

    def run_job(label, argv):
        log = log_for(argv, label)
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "w") as lf:
            proc = subprocess.run(argv, stdout=lf, stderr=subprocess.STDOUT)
        return label, proc.returncode, log

    failures = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(run_job, label, argv) for label, argv in jobs]
        for fut in futures:
            label, rc, log = fut.result()
            if rc != 0:
                tail = log.read_text(errors="replace").strip().splitlines()[-8:]
                failures.append(f"{label} failed (rc={rc}):\n" + "\n".join(tail))
    done.set()
    monitor.join(timeout=2)
    if failures:
        raise FarmError("\n".join(failures))
    proc = subprocess.run(plan["join"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise FarmError(f"join failed:\n{proc.stderr.strip()[-800:]}")
    return 0


# --------------------------------------------------------------------------
# Verification: exit code 0 is not evidence (issue #88).


def verify_output(out, reference, *, ffprobe, strict_streams):
    """Problems found, empty when the output matches its reference.

    Duration within SEAM_TOLERANCE_S always; stream count always (a silently
    dropped audio stream is the classic silent bug); fps/frame counts when
    both sides report them; codec/geometry only against an explicit
    --reference, because a caller's recipe may legitimately change them
    relative to the source.
    """
    o = probe(out, ffprobe)
    r = probe(reference, ffprobe)
    problems = []
    if abs(o["duration"] - r["duration"]) > SEAM_TOLERANCE_S:
        problems.append(f"duration {o['duration']:.3f}s vs reference "
                        f"{r['duration']:.3f}s (tolerance {SEAM_TOLERANCE_S}s)")
    if len(o["stream_kinds"]) != len(r["stream_kinds"]):
        problems.append(f"stream count {len(o['stream_kinds'])} vs "
                        f"{len(r['stream_kinds'])} ({o['stream_kinds']} vs "
                        f"{r['stream_kinds']})")
    if o["frame_count"] and r["frame_count"] and o["fps"] == r["fps"]:
        if o["frame_count"] != r["frame_count"]:
            problems.append(f"frame count {o['frame_count']} vs "
                            f"{r['frame_count']} — a seam dropped or "
                            f"duplicated a frame")
    if strict_streams:
        for key in ("codec_name", "width", "height", "pix_fmt"):
            if o[key] != r[key]:
                problems.append(f"{key} {o[key]} vs reference {r[key]}")
    return problems


# --------------------------------------------------------------------------
# CLI


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Encode one file on the ghost k3s cluster (or locally "
                    "with --local). The VIDEO recipe follows --; audio is a "
                    "single unsegmented pass set by --audio-args.",
        epilog="default video recipe: " + " ".join(DEFAULT_VIDEO_ARGS) +
               "   default audio: " + " ".join(DEFAULT_AUDIO_ARGS))
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--segments", type=int, default=None,
                    help="chunks to split into (default: limit-cpu/threads on "
                         "the farm, cpu-count/threads locally)")
    ap.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                    help="ffmpeg -threads per chunk (default 6; x264 scales "
                         "poorly past ~8)")
    ap.add_argument("--cpu", default=DEFAULT_CPU,
                    help="pod CPU request — kept LOW so the pod always "
                         "schedules (default 2); the limit is the real budget")
    ap.add_argument("--limit-cpu", default=DEFAULT_LIMIT_CPU,
                    help="pod CPU limit / burst ceiling (default 24 = exo-0's "
                         "free cores)")
    ap.add_argument("--memory", default=DEFAULT_MEMORY,
                    help="pod memory request (default 4Gi)")
    ap.add_argument("--limit-memory", default=DEFAULT_LIMIT_MEMORY,
                    help="pod memory limit (default 16Gi)")
    ap.add_argument("--storage", default=None,
                    help="PVC size (default: 3x the source, min 1Gi)")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    ap.add_argument("--node", default=DEFAULT_NODE,
                    help="pin every segment to one node. Default: unpinned, "
                         "so the scheduler uses the whole farm")
    ap.add_argument("--kubeconfig", default=None,
                    help="default: kubectl's own resolution ($KUBECONFIG, "
                         "~/.kube/config)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--audio-args", default=" ".join(DEFAULT_AUDIO_ARGS),
                    help="one continuous audio pass, applied to the whole "
                         "file (default: '-c:a copy' — never a generation "
                         "lost). Re-encode with e.g. '-c:a aac -b:a 192k'")
    ap.add_argument("--reference", default=None,
                    help="verify against this file instead of the source, and "
                         "compare codec/geometry too")
    ap.add_argument("--keep", action="store_true",
                    help="keep the Workflow and PVC for debugging")
    ap.add_argument("--local", action="store_true",
                    help="force local execution (also the automatic fallback "
                         "when the cluster is unreachable)")
    ap.add_argument("--dry-run", action="store_true")
    # Split at "--" by hand: argparse.REMAINDER swallows every option that
    # follows the source positional, which is the opposite of helpful.
    argv = list(sys.argv[1:] if argv is None else argv)
    video_args = DEFAULT_VIDEO_ARGS
    if "--" in argv:
        cut = argv.index("--")
        argv, video_args = argv[:cut], argv[cut + 1:] or DEFAULT_VIDEO_ARGS
    args = ap.parse_args(argv)
    audio_args = shlex.split(args.audio_args)

    src, out = Path(args.source), Path(args.out)
    if not src.exists():
        raise SystemExit(f"source does not exist: {src}")
    out_name = Path(out.name).name  # basename only inside the pod

    try:
        ffprobe = find_ffprobe()
    except RuntimeError as exc:
        raise SystemExit(f"farm: {exc}")

    facts = probe(src, ffprobe)
    print(f"farm: {src}  {facts['width']}x{facts['height']} "
          f"{facts['codec_name']} {float(facts['fps']):.3f}fps "
          f"{facts['duration']:.3f}s")

    # Pick the executor before the plan: the default segment count depends on
    # whose CPUs do the work.
    if args.local:
        use_cluster, why = False, "--local given"
    else:
        use_cluster, why = cluster_available(args.kubeconfig, args.namespace)
    if use_cluster:
        segments = args.segments or max(1, int(args.limit_cpu) // args.threads)
        plan = build_plan(facts=facts, out_name=out_name, segments=segments,
                          video_args=video_args, audio_args=audio_args,
                          threads=args.threads, work_dir=WORK_DIR,
                          src_arg=f"{WORK_DIR}/in/{src.name}")
    else:
        if not args.local:
            print(f"farm: cluster unreachable ({why}); falling back to a "
                  f"local encode — fix kubectl/KUBECONFIG to use the farm")
        workers = max(1, (os.cpu_count() or 8) // args.threads)
        segments = args.segments or workers
        # rendering.md: intermediates live BESIDE the output, never in /tmp —
        # the resolved ffmpeg is usually a container that only mounts $HOME.
        parent = out.parent.resolve()
        if not str(parent).startswith(str(Path.home())):
            parent = Path(".")
        if args.dry_run:
            tmp = parent / f".farm-{out_name}-DRYRUN"
        else:
            tmp = Path(tempfile.mkdtemp(prefix=f".farm-{out_name}-", dir=parent))
        plan = build_plan(facts=facts, out_name=out_name, segments=segments,
                          video_args=video_args, audio_args=audio_args,
                          threads=args.threads, work_dir=str(tmp),
                          src_arg=str(src.resolve()),
                          ffmpeg=tuple(find_ffmpeg()))

    if args.dry_run:
        print(f"farm: {'cluster' if use_cluster else 'local'} plan, "
              f"{len(plan['chunks'])} chunks")
        for c in plan["chunks"]:
            print("  " + shlex.join(c["argv"]))
        print("  " + shlex.join(plan["join"]))
        if use_cluster:
            script = pod_script(plan)
            print(json.dumps(build_workflow(
                farm_name(src.name), script, namespace=args.namespace,
                image=args.image, cpu=args.cpu, limit_cpu=args.limit_cpu,
                memory=args.memory, limit_memory=args.limit_memory,
                node=args.node,
                service_account=DEFAULT_SERVICE_ACCOUNT,
                keep=args.keep), indent=2))
        return 0

    reference = Path(args.reference) if args.reference else src
    t0 = time.monotonic()
    try:
        if use_cluster:
            name = farm_name(src.name)
            script = pod_script(plan)
            kc = Kubectl(args.kubeconfig, args.namespace)
            run_on_cluster(plan, name=name, src=src, out=out, script=script,
                           kc=kc, image=args.image, cpu=args.cpu,
                           limit_cpu=args.limit_cpu, memory=args.memory,
                           limit_memory=args.limit_memory, node=args.node,
                           service_account=DEFAULT_SERVICE_ACCOUNT,
                           storage=args.storage or storage_for(src.stat().st_size),
                           keep=args.keep, timeout=args.timeout)
        else:
            try:
                run_locally(plan, workers=workers)
                Path(plan["join"][-1]).rename(out)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    except FarmError as exc:
        raise SystemExit(f"farm: {exc}")

    elapsed = time.monotonic() - t0
    print(f"farm: encoded in {elapsed:.0f}s "
          f"({'cluster' if use_cluster else 'local'})")

    try:
        problems = verify_output(out, reference, ffprobe=ffprobe,
                                 strict_streams=args.reference is not None)
    except FarmError as exc:
        raise SystemExit(f"farm: {exc}")
    if problems:
        for p in problems:
            print(f"farm: VERIFY FAIL: {p}")
        raise SystemExit("farm: output does not match its reference — "
                         "do not ship it (see issue #88)")
    o = probe(out, ffprobe)
    print(f"farm: verify ok — {out}  {o['duration']:.3f}s, "
          f"{o['codec_name']} {o['width']}x{o['height']}, "
          f"{o['frame_count'] or '?'} frames vs {reference}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
