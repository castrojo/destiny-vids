"""The read-through script is an output, and it stays current.

`chapters/full-script.md` exists so the whole programme can be read in one
sitting. That is only worth anything if it says what the chapter files say --
a script that has drifted is worse than no script, because it reads exactly
like one that has not.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import generate_full_script as gfs  # noqa: E402


def test_the_committed_script_is_what_the_generator_produces():
    assert gfs.OUT.read_text(encoding="utf-8") == gfs.render(gfs.collect())


def test_check_agrees_from_the_command_line():
    """The same assertion the way a person runs it, exit code and all."""
    done = subprocess.run(
        [sys.executable, "scripts/generate_full_script.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_every_act_names_where_its_copy_is_edited():
    """A read-through that does not say where to edit sends nobody anywhere."""
    text = gfs.OUT.read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert len(headings) >= 8
    assert text.count("Edit in `") == len(headings)


def test_a_nameplate_is_never_read_as_dialogue():
    """Crediting a real person is not the same as them saying something."""
    assert gfs.speech({"copy_source": "casting", "name": "Someone Real"}) is None
    assert gfs.speech({"copy_source": "brief", "name": "Someone Real"}) is None


def test_a_card_with_several_lines_is_read_out_in_full():
    """The birthday card is three fields; showing one drops two thirds."""
    said = gfs.speech({"eyebrow": "Happy Tenth Birthday",
                       "name": "RAFAEL CASTRO",
                       "body": '"We love you" - Mom and Dad'})
    assert said == ('Happy Tenth Birthday / RAFAEL CASTRO / '
                    '"We love you" - Mom and Dad')


def test_act_two_is_read_from_its_manifest_and_says_so():
    """Act II is the one act still generated in Python. Say it out loud."""
    text = gfs.OUT.read_text(encoding="utf-8")
    assert "scripts/build_efmb_plates.py" in text


def test_act_two_lines_are_not_printed_twice():
    """Its chapter file's two splashes are in its manifest as well."""
    blocks = gfs.collect()
    assert [act for _, act, _, _ in blocks].count("II") == 1


def test_the_show_reads_in_programme_order():
    starts = [start for start, _, _, _ in gfs.collect()]
    assert starts == sorted(starts)
