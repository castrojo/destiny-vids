"""Live proof: encode the megacut's Act VI segment on the cluster via the
new generic path (tools/farm.py run_ffmpeg_on_cluster), invoked exactly the
way tools/megacut.py's farm mode invokes it."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import megacut, farm  # noqa: E402

plan = megacut.load_plan("stories/megacut/megacut.json")
idx = next(i for i, it in enumerate(plan["items"])
           if it["kind"] == "clip" and "06-7daystothewolves" in it.get("path", ""))
item = plan["items"][idx]
out = Path("work/farm-proof/seg-proof.mkv").resolve()
out.parent.mkdir(parents=True, exist_ok=True)
argv = megacut.build_segment_command(plan, idx, out, threads=8)
print(f"proof: item {idx} ({item.get('label', '')[:60]})", flush=True)
print(f"proof: local argv[0] = {argv[0]}", flush=True)
t0 = time.monotonic()
facts = farm.run_ffmpeg_on_cluster(
    argv, inputs=[megacut.resolve(item["path"])], out=out,
    expected_duration=megacut.item_duration(item),
    ffprobe=[megacut.ffprobe_bin()])
print(f"PROOF DONE in {time.monotonic() - t0:.0f}s — "
      f"{facts['duration']:.3f}s {facts['codec_name']}", flush=True)
