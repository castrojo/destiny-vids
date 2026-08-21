"""Which plates go by faster than anybody can read them.

``tools/plate.py`` already knows that a plate the viewer cannot finish is
worse than no plate -- ``MIN_HOLD = 2.2`` exists for exactly that reason. But
``MIN_HOLD`` is a floor for *any* plate, and nothing has ever checked a hold
against the length of the words in it. ``dur`` is authored by hand, so a
two-word pill and a twelve-word pill can both sit on screen for 1.2 seconds,
and only one of them is readable.

This reports the difference. It is a REPORT: a hold that is too short is a
punch-list item, and re-timing an authored beat is the owner's call, never a
tool's -- ``AGENTS.md``, on moving copy the owner already placed. So the
default exit is 0. ``--check`` exits non-zero for anybody gating a *final*
cut, the same shape as ``tools/placeholder.py``.

**The model.** Characters per second, which is what subtitling uses, because
these pills are one unwrapped line of chat and the viewer is also watching a
film. The default of 17 CPS is the common broadcast figure for adult reading
while attending to picture; ``--cps`` moves it. A plate must clear both the
CPS estimate and ``MIN_HOLD``. At 17 CPS the rate term only bites above 37
characters, so below that this says exactly what ``plate.py``'s floor already
said -- which is why the report separates the two. Only "short of its own
copy" is this tool's own finding.

The estimate deliberately under-states in two ways. ``chars`` counts ``text``
alone, though the pill also draws a speaker eyebrow; and ``plate.py`` shrinks
type from 28px to a 19px floor to fit a 1550px pill, so the longest lines
render smallest -- exactly where a linear model is least generous. A report
that overstates gets argued with instead of acted on.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The floor `tools/plate.py` already applies, imported rather than copied so
# the two cannot drift.
try:
    from tools.plate import MIN_HOLD
except ImportError:  # running as a script from the repo root
    sys.path.insert(0, str(REPO_ROOT))
    from tools.plate import MIN_HOLD

# Characters per second. Subtitling's comfortable rate for an adult reading
# while watching picture; Netflix's English guideline is 17.
DEFAULT_CPS = 17.0

# Plate kinds whose text is prose the viewer reads at chat speed. A title
# card, a menu, a Guardian nameplate and a day card are read differently --
# usually they are the only thing on screen, and they are composed rather
# than spoken -- so they are counted as skipped rather than judged.
PROSE_KINDS = {"chat", "banner", "ending"}

STORY_DIRS = ("stories",)

UNREADABLE = ("cannot be read", "is not valid JSON")


def _num(value):
    """A timing field as a float, or None if it is not a number.

    Degrade, never block: one string where a number belongs must cost its own
    plate a measurement, not abort the audit of every other plate.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def required_hold(text: str, cps: float = DEFAULT_CPS) -> float:
    """The shortest hold in which ``text`` can be read, in seconds."""
    if not text:
        return MIN_HOLD
    return max(MIN_HOLD, len(text) / cps)


def windows(plate: dict):
    """``(on_screen, opaque, quirk)``, or None if the plate cannot be timed.

    ``on_screen`` is the generous reading: every second any part of the plate
    is up. ``opaque`` is the strict one: only while the words are at full
    strength. The verdict is taken on ``on_screen``, deliberately -- a viewer
    finishes a line that is on its way out, and a report that overstates gets
    argued with instead of acted on. ``opaque`` is printed beside it because
    the gap is worth seeing on its own: a 1.2s pill with a 0.6s fade-in is
    legible for a quarter of its own life.

    **``at + dur`` is a hard end.** Both renderers gate the overlay on it --
    ``scripts/actbuild.py`` with ``enable='between(t,at,at+dur)'`` and
    ``scripts/build_europa.py`` with ``gte(t,at)*lt(t,at+dur)`` -- so a fade
    tail scheduled past it is clipped, never shown. Crediting it would make
    the generous number generous by accident rather than on purpose.

    ``quirk`` names a timing record that disagrees with itself: a
    ``fade_out_at`` outside the plate's own window would render it invisible
    while reading here as comfortably long. Saying so is not re-timing it.
    """
    at, dur = _num(plate.get("at")), _num(plate.get("dur"))
    if at is None or dur is None or dur < 0:
        return None

    hard_end = at + dur
    fade_in = _num(plate.get("fade_in")) or 0.0
    fade_out_at = _num(plate.get("fade_out_at"))

    quirk = None
    if fade_out_at is not None and not (at <= fade_out_at <= hard_end):
        quirk = (f"fade_out_at {fade_out_at:g} falls outside its own window "
                 f"{at:g}-{hard_end:g}, so the plate renders invisible")
    elif fade_in > dur:
        quirk = (f"fade_in {fade_in:g}s is longer than the {dur:g}s the "
                 f"plate is up")

    on_screen = max(0.0, hard_end - at)

    opaque_start = min(at + fade_in, hard_end)
    opaque_end = hard_end
    if fade_out_at is not None and at <= fade_out_at <= hard_end:
        opaque_end = fade_out_at
    return on_screen, max(0.0, opaque_end - opaque_start), quirk


def plate_text(plate: dict) -> str:
    """The words a viewer has to read on this plate."""
    for key in ("text", "message", "body"):
        value = plate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _display(path: Path) -> str:
    """Repo-relative where possible, and whatever was given where not.

    A manifest passed on the command line can sit anywhere -- a scratch copy
    in /tmp while somebody tries a re-time before committing it. Naming the
    file must never be the thing that fails.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def audit_manifest(path: Path, cps: float = DEFAULT_CPS):
    """``(short, skipped, problems)`` for one manifest.

    ``problems`` carries anything that stopped a plate being measured, so a
    file that could not be read cannot masquerade as a file with nothing
    wrong in it. That distinction is the whole difference between "I looked
    and it is fine" and "I did not look", and it is the one direction in
    which this tool must never be quietly wrong.
    """
    short: list[dict] = []
    skipped: Counter = Counter()
    problems: list[str] = []

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return short, skipped, [
            f"{_display(path)}: cannot be read ({exc.strerror or exc})"]
    except ValueError as exc:
        return short, skipped, [f"{_display(path)}: is not valid JSON ({exc})"]

    if not isinstance(doc, dict) or not isinstance(doc.get("plates"), list):
        return short, skipped, problems

    for plate in doc["plates"]:
        if not isinstance(plate, dict):
            continue
        text = plate_text(plate)
        if not text:
            continue
        kind = plate.get("kind")
        if kind is not None and kind not in PROSE_KINDS:
            skipped[kind] += 1
            continue

        plate_id = plate.get("id") or "<no id>"
        measured = windows(plate)
        if measured is None:
            problems.append(
                f"{_display(path)}: plate {plate_id} carries {len(text)} "
                f"characters and cannot be timed (at={plate.get('at')!r} "
                f"dur={plate.get('dur')!r})")
            continue
        on_screen, opaque, quirk = measured
        if quirk:
            problems.append(f"{_display(path)}: plate {plate_id} {quirk}")

        need = required_hold(text, cps)
        if on_screen + 1e-6 >= need:
            continue
        short.append({
            "manifest": _display(path),
            "id": plate_id,
            "speaker": plate.get("speaker") or "",
            "chars": len(text),
            "on_screen": round(on_screen, 3),
            "opaque": round(opaque, 3),
            "need": round(need, 3),
            "deficit": round(need - on_screen, 3),
            # Below ~37 chars at 17 cps the floor is what binds, and the floor
            # is something plate.py already knew. Only the rate-driven rows
            # are this tool's own finding.
            "rate_driven": need > MIN_HOLD + 1e-9,
            "text": text,
        })
    return short, skipped, problems


def manifests(root: Path) -> list[Path]:
    found = []
    for directory in STORY_DIRS:
        base = root / directory
        if base.is_dir():
            found.extend(sorted(base.rglob("*.json")))
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Report chat plates held too briefly to be read.")
    ap.add_argument("manifest", nargs="*", type=Path,
                    help="manifests to audit (default: every stories/*.json)")
    ap.add_argument("--cps", type=float, default=DEFAULT_CPS,
                    help=f"reading rate in characters per second "
                         f"(default {DEFAULT_CPS:g})")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any plate is short, or if anything could "
                         "not be measured -- for gating a FINAL cut only. The "
                         "default reports and exits 0, because re-timing an "
                         "authored beat is the owner's call")
    args = ap.parse_args(argv)

    paths = args.manifest or manifests(REPO_ROOT)
    short: list[dict] = []
    skipped: Counter = Counter()
    problems: list[str] = []
    unread = 0
    for path in paths:
        rows, skips, probs = audit_manifest(path, args.cps)
        short.extend(rows)
        skipped.update(skips)
        problems.extend(probs)
        if any(mark in p for p in probs for mark in UNREADABLE):
            unread += 1

    if short:
        short.sort(key=lambda row: -row["deficit"])
        by_manifest: dict[str, list[dict]] = {}
        for row in short:
            by_manifest.setdefault(row["manifest"], []).append(row)

        rate = sum(1 for row in short if row["rate_driven"])
        print(f"{len(short)} plate(s) held below a readable hold at "
              f"{args.cps:g} cps -- {rate} short of their own copy, "
              f"{len(short) - rate} short of the {MIN_HOLD}s floor "
              f"tools/plate.py already applies:\n")
        for manifest, rows in by_manifest.items():
            print(f"  {manifest}")
            for row in rows:
                why = "copy" if row["rate_driven"] else "floor"
                print(f"    {row['id']:<28} {row['on_screen']:>5.2f}s up "
                      f"({row['opaque']:.2f}s opaque), needs "
                      f"{row['need']:>5.2f}s [{why}]  -- short "
                      f"{row['deficit']:.2f}s, {row['chars']} chars")
                speaker = f"{row['speaker']}: " if row["speaker"] else ""
                print(f"      {speaker}{row['text']}")
            print()
    else:
        print(f"0 plate(s) held below a readable hold at {args.cps:g} cps")

    print(f"read {len(paths) - unread} of {len(paths)} manifest(s)")
    if skipped:
        kinds = ", ".join(f"{kind} {n}" for kind, n in skipped.most_common())
        print(f"not judged: {sum(skipped.values())} plate(s) of other kinds "
              f"({kinds}) -- a title card or a menu is not read at chat speed")

    if problems:
        print(f"\n{len(problems)} thing(s) could not be measured, which is "
              f"NOT the same as nothing being wrong:")
        for problem in problems:
            print(f"  - {problem}")

    if short:
        print("\nThis is a punch-list, not a verdict. Widening a hold moves "
              "whatever is seated\nafter it, so which of these is worth the "
              "shove is an editorial call -- and\nmoving an authored beat is "
              "the owner's, not a tool's.")

    if args.check:
        return 1 if (short or problems) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
