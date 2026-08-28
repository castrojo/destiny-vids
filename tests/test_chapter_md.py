"""Chapter-file conversation authoring (tools/chapter_md.py).

The format is the contract the owner writes against: one `## <programme
time>` heading per conversation, `Speaker: line` rows under it, readability
timing derived, pins honoured exactly with the shift recorded.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_efmb  # noqa: E402
import build_efmb_plates  # noqa: E402
from tools import chapter_md  # noqa: E402

OFFSET = chapter_md.ACT_PROGRAMME_START["II"]


def schedule(md, seats=None):
    blocks = chapter_md.parse(md)
    assert len(blocks) == 1
    return chapter_md.schedule_block(blocks[0], OFFSET, seats=seats)


SPOKEN = {"film": 200.0, "src": 358.24,
          "matched": "I'm so proud of you kids!"}


def test_a_line_matching_the_video_is_seated_where_it_is_spoken():
    at, _, notes = schedule(
        "## 6:45\nKarena: I'm so proud of you kids!\n",
        seats=[SPOKEN])
    assert at[0] == pytest.approx(200.0, abs=1e-3)
    assert any("seated on" in n and "5:58.24" in n for n in notes)


def test_a_pin_overrides_the_speech_seat_and_says_so():
    at, _, notes = schedule(
        "## 6:45\nKarena @ 6:50: I'm so proud of you kids!\n",
        seats=[SPOKEN])
    assert at[0] == pytest.approx(410.0 - OFFSET, abs=1e-3)
    assert any("pinned away from" in n and "the pin stands" in n
               for n in notes)


def test_a_speech_seat_earlier_than_the_cascade_is_recorded():
    at, _, notes = schedule(
        "## 6:45\n"
        "Karena: A first line with some length to it\n"
        "jrsapi: I'm so proud of you kids!\n",
        seats=[None, {**SPOKEN, "film": 405.5 - OFFSET}])
    assert at[1] == pytest.approx(405.5 - OFFSET, abs=1e-3)
    assert any("overlap" in n for n in notes)


def test_seat_lines_matches_paraphrase_and_skips_cut_frames(monkeypatch):
    monkeypatch.setattr(chapter_md, "sync_seats",
                        lambda act: [(358.24, "I'm so proud of you kids!")])
    monkeypatch.setattr(chapter_md, "film_for_source",
                        lambda act, src: 200.0 if src < 359 else None)
    lines = [{"speaker": "K", "kind": "chat", "pin": None,
              "text": "I am so proud of you kids"},
             {"speaker": "K", "kind": "chat", "pin": None,
              "text": "unrelated words entirely"},
             {"speaker": "K", "kind": "chat", "pin": 400.0,
              "text": "I'm so proud of you kids!"}]
    seats = chapter_md.seat_lines("II", lines)
    assert seats[0]["film"] == 200.0
    assert seats[1] is None
    # A pinned line still gets its seat computed -- the operator is told
    # what the evidence preferred even though the pin wins.
    assert seats[2]["film"] == 200.0


def test_seat_lines_without_a_dialogue_record_is_quiet(monkeypatch):
    monkeypatch.setattr(chapter_md, "ACT_SOURCES", {})
    lines = [{"speaker": "K", "kind": "chat", "pin": None, "text": "anything"}]
    assert chapter_md.seat_lines("II", lines) == [None]


def test_one_heading_drops_a_whole_conversation():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena: Hit 'em with your lessons learned\n"
        "Rochaporto: One reference architecture coming up!\n"
        "jrsapi: Shit are you taking notes?\n")
    # The block lands on the PROGRAMME clock: 6:45 minus act II's start.
    assert at[0] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    # Every line is its own pill, chained by read time plus the beat.
    assert at[1] == pytest.approx(at[0] + holds[0] + chapter_md.GAP)
    assert at[2] == pytest.approx(at[1] + holds[1] + chapter_md.GAP)
    assert notes == []


def test_read_time_is_the_clock_and_it_is_clamped():
    assert chapter_md.hold_for("Hi") == chapter_md.MIN_HOLD
    assert chapter_md.hold_for("x" * 400) == chapter_md.MAX_HOLD
    mid = "One reference architecture coming up!"  # 37 chars
    assert chapter_md.hold_for(mid) == pytest.approx(len(mid) / 15.0,
                                                     abs=1e-3)


def test_a_pin_reseats_one_line_and_the_rest_adjust():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena: Hit 'em with your lessons learned\n"
        "jrsapi @ 6:52: Shit are you taking notes?\n"
        "Karena: Like cardio!\n")
    # The pin is exact, on the programme clock.
    assert at[1] == pytest.approx(412.0 - OFFSET, abs=1e-3)
    # The heading still seats the first line; the slack before the pin is
    # silence, and the line after the pin cascades off it.
    assert at[0] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    assert at[2] == pytest.approx(at[1] + holds[1] + chapter_md.GAP)
    assert notes == []


def test_a_pin_that_overruns_its_neighbour_is_recorded_not_raised():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena @ 6:45: Hit 'em with your lessons learned\n"
        "jrsapi @ 6:46: Shit are you taking notes?\n")
    assert at[1] == pytest.approx(406.0 - OFFSET, abs=1e-3)
    assert any("overlap" in n for n in notes)


def test_a_pinned_first_line_disagrees_with_its_heading_and_says_so():
    at, _, notes = schedule(
        "## 6:45\n"
        "Karena @ 6:50: Hit 'em with your lessons learned\n")
    assert at[0] == pytest.approx(410.0 - OFFSET, abs=1e-3)
    assert any("the pin wins" in n for n in notes)


def test_consecutive_lines_by_one_speaker_are_separate_pills():
    blocks = chapter_md.parse(
        "## 6:45\nKarena: first\nKarena: second\nKarena: third\n")
    assert [l["speaker"] for l in blocks[0]["lines"]] == ["Karena"] * 3


def test_entries_shape_matches_the_act_build():
    md = ("## 6:45\n"
          "rochaporto: One reference architecture coming up!\n"
          "Karena: Like cardio!\n")
    blocks = chapter_md.parse(md)
    at, holds, _ = chapter_md.schedule_block(blocks[0], OFFSET)
    assert chapter_md.LOGIN_SHAPE.match("rochaporto")
    assert not chapter_md.LOGIN_SHAPE.match("Karena")


def test_entries_from_the_committed_file_are_manifest_shaped(tmp_path):
    entries, unresolved = chapter_md.entries("II")
    # An explicit `+hold` is honoured verbatim, even below the derived floor
    # (the retirement pair keeps act III's authored 2.125); the floor guards
    # only holds nobody authored.
    explicit = {
        line["id"]
        for block in chapter_md.parse(
            chapter_md.chapter("II").path.read_text(encoding="utf-8"))
        for line in block["lines"]
        if line.get("hold") is not None
    }
    for e in entries:
        assert e["copy_source"] == "owner_supplied"
        if e["id"] not in explicit:
            assert e["dur"] >= chapter_md.MIN_HOLD
        assert e["at"] >= 0
        if e["kind"] == "chat":
            assert e["speaker"] and "text" in e
        else:
            assert e["kind"] == "miniboss" and e["name"]


def chapter_for(tmp_path, body, act="II", programme_start=None):
    """A throwaway ``Chapter`` over ``body``, for a test that fakes ``chapter()``.

    Bypasses ``discover()`` entirely -- no file is wired to an act -- so a
    test can hand ``chapter_md.chapter`` a block it wrote inline without
    touching the committed act II chapter file.
    """
    path = tmp_path / "chapter.md"
    path.write_text(body, encoding="utf-8")
    if programme_start is None:
        programme_start = chapter_md.ACT_PROGRAMME_START["II"]
    return chapter_md.Chapter(
        path, {"act": act, "programme_start": programme_start}, body)


def test_block_end_includes_the_final_hold_and_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(chapter_md, "chapter",
                        lambda _act: chapter_for(tmp_path,
                            "## 9:52.203 paused\n"
                            "kolunmi: First\nkolunmi: Second\n"))
    end = chapter_md.block_end("II", "paused")
    assert end == pytest.approx(
        592.203 - chapter_md.ACT_PROGRAMME_START["II"]
        + chapter_md.MIN_HOLD * 2 + chapter_md.GAP * 2)


def test_block_end_raises_for_an_unknown_label():
    with pytest.raises(KeyError):
        chapter_md.block_end("II", "no-such-block-label")


def test_entries_can_retain_a_block_label_for_a_builder(tmp_path, monkeypatch):
    monkeypatch.setattr(chapter_md, "chapter",
                        lambda _act: chapter_for(tmp_path,
                            "## 9:52.203 paused\nkolunmi: First\n"))
    entries, _ = chapter_md.entries("II", include_block_labels=True)
    assert entries[0]["_chapter_label"] == "paused"


def test_entries_default_shape_never_carries_a_block_label(tmp_path, monkeypatch):
    monkeypatch.setattr(chapter_md, "chapter",
                        lambda _act: chapter_for(tmp_path,
                            "## 9:52.203 paused\nkolunmi: First\n"))
    entries, _ = chapter_md.entries("II")
    assert "_chapter_label" not in entries[0]


# --- the seat the BUILD emits ---------------------------------------------
#
# `entries` is what the chapter file says; an act whose builder moves a line
# between the file and the manifest (act II) needs `show` and `check` to
# describe the film that ships instead. The mapping lives in the builder and
# is reached through the `reseat` hook the chapter file declares.

RESEAT_MODULE = """
def reseat(entries):
    for entry in entries:
        entry.pop("_chapter_label", None)
        entry["at"] = round(entry["at"] + 10.0, 3)
    return entries
"""


def test_emitted_entries_applies_the_declared_reseat_hook(tmp_path,
                                                          monkeypatch):
    hook = tmp_path / "fake_builder.py"
    hook.write_text(RESEAT_MODULE, encoding="utf-8")
    chap = chapter_for(tmp_path, "## 9:52.203 paused\nkolunmi: First\n")
    chap.fields["reseat"] = f"{hook}:reseat"
    monkeypatch.setattr(chapter_md, "chapter", lambda _act: chap)
    raw, _ = chapter_md.entries("II")
    emitted, notes = chapter_md.emitted_entries("II")
    assert notes == []
    assert emitted[0]["at"] == pytest.approx(raw[0]["at"] + 10.0)
    assert "_chapter_label" not in emitted[0]


def test_a_chapter_with_no_reseat_hook_emits_what_it_resolves(tmp_path,
                                                              monkeypatch):
    monkeypatch.setattr(chapter_md, "chapter",
                        lambda _act: chapter_for(tmp_path,
                            "## 9:52.203\nkolunmi: First\n"))
    assert chapter_md.emitted_entries("II") == chapter_md.entries("II")


def test_a_reseat_hook_that_cannot_be_loaded_degrades_and_says_so(
        tmp_path, monkeypatch):
    """A preview one release out of date beats a traceback.

    Somebody reading their own dialogue back is not the person who can fix
    a builder that has moved, so a hook that fails to import reports the
    fact and keeps showing the file's own schedule.
    """
    chap = chapter_for(tmp_path, "## 9:52.203\nkolunmi: First\n")
    chap.fields["reseat"] = "scripts/no_such_builder.py:reseat"
    monkeypatch.setattr(chapter_md, "chapter", lambda _act: chap)
    emitted, notes = chapter_md.emitted_entries("II")
    assert any("reseat hook" in note for note in notes)
    assert emitted[0]["at"] == pytest.approx(
        chapter_md.entries("II")[0][0]["at"])
    assert "_chapter_label" not in emitted[0]


def test_act_two_reseats_through_its_builder_and_not_a_second_copy():
    """One mapping, reached from both ends.

    The regression this pins: `build_efmb_plates.build()` grew the rebase
    and the `source_anchor` seating, and `chapter_md`'s own commands kept
    printing the raw schedule. Restating the arithmetic here rather than
    calling the builder's own function would put the same defect back, one
    copy later.
    """
    hook, note = chapter_md._reseater("II")
    assert note is None
    assert hook is build_efmb_plates.reseat_chapter_entries


def test_act_two_check_reports_no_drift():
    """`check II` is act II's drift gate again, not ten permanent lines.

    Read with tests/test_efmb_act.py::
    test_the_committed_manifest_matches_its_generator, which pins the
    committed manifest to what `build_efmb_plates.py --write` emits: the two
    together say `check II` is clean immediately after a regeneration, so a
    real copyedit that never reached the manifest still shows up here.
    """
    assert chapter_md.check("II") == []
    assert chapter_md.main(["check", "II", "--check"]) == 0


def _shown(capsys, act="II"):
    chapter_md.main(["show", act])
    return capsys.readouterr().out.splitlines()


def test_show_quotes_act_two_at_the_seats_the_manifest_carries(capsys):
    """The clock `show` prints is the clock the owner scrubs.

    Every post-hallway act II line is rebased by the grown `paused` block
    before it reaches the manifest. Printing the pre-rebase seat sent an
    editor asked to nudge `retirement-1` to a timecode 47 s from the picture
    they meant to move.
    """
    lines = _shown(capsys)
    plates = {p["id"]: p for p in chapter_md.manifest_plates("II")}
    offset = chapter_md.ACT_PROGRAMME_START["II"]
    for plate_id, tail in (("mapped_haters", "! HATERS"),
                           ("retirement-1", "castrojo: Finally, retirement"),
                           ("chat_kolunmi_level", "kolunmi: Hey did you see "
                            "how we just loaded up in a new level?")):
        at = plates[plate_id]["at"]
        shown = [line for line in lines if line.endswith(tail)]
        assert len(shown) == 1, f"{plate_id} is not shown exactly once"
        assert f"{chapter_md.format_tc(at + offset)} programme" in shown[0]
        assert f"{chapter_md.format_tc(at)} film" in shown[0]
        assert "reseated by the build" in shown[0]


def test_show_seats_sup_on_the_heroes_void_shield_source(capsys):
    """Sup is bound to the heroes' shield formation, not the queue."""
    shown = [line for line in _shown(capsys)
             if line.endswith("kylegospo: Sup")]
    assert len(shown) == 1
    sup = {p["id"]: p for p in chapter_md.manifest_plates("II")}["mapped_kyle_sup"]
    assert sup["seen_at_src"] == pytest.approx(331.763)
    at = build_efmb.edited_film_for_source(331.763)
    assert sup["at"] == pytest.approx(round(at, 3))
    assert f"{chapter_md.format_tc(sup['at'])} film" in shown[0]
    assert (f"{chapter_md.format_tc(sup['at'] + chapter_md.ACT_PROGRAMME_START['II'])}"
            " programme") in shown[0]


# Act II's own declared column order (chapters/II-endless-forms.md front
# matter), reproduced here -- across the SAME three physical lines the real
# file declares it on -- so the ordering test below exercises
# `parse_front_matter`'s continuation-line joining directly, and needs
# neither the real chapter file nor Task 3's still-missing `paused` heading
# label. See also `test_parse_front_matter_joins_a_wrapped_scalar_field`
# below, which asserts the joining in isolation, and
# `test_the_real_act_ii_field_order_survives_its_multiline_declaration`,
# which pins the same shape against `chapters/II-endless-forms.md` itself.
ACT_II_FIELD_ORDER = (
    "id, at, dur, name, title, title_source, kind, position,\n"
    "  copy_source, speaker, text, text_source, scale, seen_at_src,\n"
    "  avatar, avatar_url, bond_of")


def test_parse_front_matter_joins_a_wrapped_scalar_field():
    """A continuation line with no `defaults:` section open extends the
    top-level scalar it follows, rather than being parsed as its own bogus
    key (task-2-rereview-1.md: the un-joined tail silently dropped every
    name after the first line's trailing comma, `field_order` truncated to
    `..., kind, position,`)."""
    text = "---\nact: X\nfield_order: " + ACT_II_FIELD_ORDER + "\n---\n"
    fields, _ = chapter_md.parse_front_matter(text)
    order = [k.strip() for k in fields["field_order"].split(",")]
    assert order == [
        "id", "at", "dur", "name", "title", "title_source", "kind",
        "position", "copy_source", "speaker", "text", "text_source",
        "scale", "seen_at_src", "avatar", "avatar_url", "bond_of"]


def test_the_real_act_ii_field_order_survives_its_multiline_declaration():
    """`chapters/II-endless-forms.md` wraps its `field_order` across three
    physical lines (task-2-rereview-1.md). Read straight from disk, not a
    fixture, so a future re-wrap of the same field cannot silently
    reintroduce the truncation."""
    text = (REPO_ROOT / "chapters" / "II-endless-forms.md").read_text()
    fields, _ = chapter_md.parse_front_matter(text)
    order = [k.strip() for k in fields["field_order"].split(",")]
    assert "seen_at_src" in order
    assert order.index("seen_at_src") < order.index("avatar")
    assert order.index("seen_at_src") < order.index("avatar_url")
    assert order.index("seen_at_src") < order.index("bond_of")


def test_a_key_added_after_the_chapter_file_builds_still_lands_in_order():
    """Reproduces the ordering bug fixed in build_efmb_plates.py's build().

    A source-anchored line (Act II's `Sup`, authored with `- source_anchor:
    <src>`) comes back from `chapter_md.entries()` with `source_anchor`
    still on it and no `seen_at_src` yet -- the recomputed source frame is
    only known once `build_efmb_plates.build()` calls its own `film_of()`.
    Assigning that key afterwards is a plain dict write, which always
    appends: `seen_at_src` used to land after `bond_of`/`avatar`/
    `avatar_url` even though the act's own `field_order` seats it ahead of
    them (mirrored above as `ACT_II_FIELD_ORDER`, wrapped exactly as the
    real chapter file wraps it). The fix re-applies `chapter_md._ordered()`
    once the key is added, which is exercised here directly since
    `scripts/build_efmb_plates.py` cannot yet be imported (it derives a
    module-level constant from the same missing `paused` label, which is
    Task 3's job, not this test's).
    """
    text = ("---\nact: X\nfield_order: " + ACT_II_FIELD_ORDER + "\n---\n\n"
            "## 0:00\n\nkylegospo @ 0:10 +2.2: Sup\n"
            "  - bond_of: mapped_kyle_reveal\n"
            "  - avatar: renders/avatars/KyleGospo.png\n"
            "  - avatar_url: https://github.com/KyleGospo.png?size=256\n"
            "  - source_anchor: 333.497\n")
    fields, _ = chapter_md.parse_front_matter(text)
    order = [k.strip() for k in fields["field_order"].split(",")]
    line = chapter_md.parse(text)[0]["lines"][0]
    entry = chapter_md.build_entry("X", 1, 1, line, line["pin"] or 0.0,
                                   line["hold"] or 1.0,
                                   fields.get("defaults") or {}, order)

    # What chapter_md hands back today: portrait keys already in their
    # declared place, `source_anchor` trailing because it names no
    # `field_order` column.
    assert list(entry.keys())[-1] == "source_anchor"

    # scripts/build_efmb_plates.py's build(): pop `source_anchor`, seat the
    # recomputed frame, set `seen_at_src`, then re-seat the whole entry.
    source_anchor = entry.pop("source_anchor")
    entry["at"] = 335.267
    entry["seen_at_src"] = source_anchor
    ordered = chapter_md._ordered(entry, order)
    entry.clear()
    entry.update(ordered)

    keys = list(entry.keys())
    assert keys.index("seen_at_src") < keys.index("avatar")
    assert keys.index("seen_at_src") < keys.index("avatar_url")
    assert keys.index("seen_at_src") < keys.index("bond_of")
    assert keys == [k for k in order if k in entry]


def test_an_unknown_act_is_not_an_error():
    assert chapter_md.entries("IX") == ([], [])


def test_timecode_forms():
    assert chapter_md.parse_tc("6:45") == 405.0
    assert chapter_md.parse_tc("6:45.50") == 405.5
    assert chapter_md.parse_tc("1:02:03.5") == 3723.5
    assert chapter_md.parse_tc("90") == 90.0


def test_a_heading_without_a_time_is_rejected():
    with pytest.raises(ValueError):
        chapter_md.parse("## not-a-time\nKarena: hi\n")


def test_a_boss_line_authors_a_red_splash():
    blocks = chapter_md.parse("## 6:45\n! POOR TECHNICAL DECISIONS\n")
    line = blocks[0]["lines"][0]
    assert line["kind"] == "boss"
    assert line["name"] == "POOR TECHNICAL DECISIONS"
    assert line["title"] is None          # no pipe: no second row


def test_a_boss_line_pipe_keeps_the_title_slot_as_placeholder():
    blocks = chapter_md.parse("## 6:45\n! [the_id] POOR TECHNICAL DECISIONS |\n")
    line = blocks[0]["lines"][0]
    assert line["id"] == "the_id"
    assert line["title"] == ""            # the slot, not the words


def test_a_boss_line_with_title_authors_the_second_row():
    blocks = chapter_md.parse("## 6:45\n! HATERS @ 10:00 | They Hate Us\n")
    line = blocks[0]["lines"][0]
    assert line["title"] == "They Hate Us"
    assert line["pin"] == 600.0


def test_boss_entries_carry_the_miniboss_shape_and_placeholder_seed():
    # The two committed red splashes are authored in the chapter file: their
    # manifest entries must keep their ids, seats and placeholder titles, so
    # the Markdown takeover changes no pixel.
    entries, _ = chapter_md.entries("II")
    by_id = {e["id"]: e for e in entries}
    flash = by_id["late_poor_technical_decisions"]
    assert flash["kind"] == "miniboss" and flash["position"] == "boss"
    assert flash["at"] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    assert flash["dur"] == chapter_md.MIN_HOLD
    assert flash["title_source"] == "placeholder"
    haters = by_id["mapped_haters"]
    assert haters["source_anchor"] == pytest.approx(326.163)


def test_instructions_prose_and_indented_examples_parse_as_nothing():
    md = chapter_md.chapter_path("II").read_text()
    blocks = chapter_md.parse(md)
    # The file carries the act's conversations AND a grammar guide written in
    # the same syntax it describes. The guide's prose, its indented examples
    # and the evidence notes beside each line must not leak in as
    # scheduleable lines: every parsed line has to be one the act declares.
    ids = {line["id"] for block in blocks for line in block["lines"]}
    assert "example" not in ids
    for block in blocks:
        for line in block["lines"]:
            assert line["kind"] in {"chat", "boss", "card"}
            assert line["id"], "a line parsed without an id"
    # And the two red splashes are still the only minibosses in the act.
    boss = [line["id"] for block in blocks for line in block["lines"]
            if line["kind"] == "boss"]
    assert boss == ["late_poor_technical_decisions", "mapped_haters"]


# ---------------------------------------------------------------------------
# The grammar the sweep added, each rule written from a bug the identity
# tests caught while acts 0, III, VI and VIII were being migrated.
# ---------------------------------------------------------------------------

def _one(text, act="X"):
    """Parse a scrap of chapter Markdown and build its single entry."""
    blocks = chapter_md.parse(text)
    fields, _ = chapter_md.parse_front_matter(text)
    defaults = fields.get("defaults") or {}
    order = fields.get("field_order")
    order = ([k.strip() for k in order.split(",")] if isinstance(order, str)
             else None)
    line = blocks[0]["lines"][0]
    return chapter_md.build_entry(act, 1, 1, line, line["pin"] or 0.0,
                                  line["hold"] or 1.0, defaults, order)


def test_an_empty_list_can_be_written():
    """Zero repeated rows is indistinguishable from an absent field."""
    entry = _one("## 0:00\n\n* thing @ 0:00 +1.0\n  - body: []\n")
    assert entry["body"] == []


def test_a_comment_does_not_detach_the_rows_below_it():
    """An owner annotating their own card must not silently lose it."""
    entry = _one("## 0:00\n\n* thing @ 0:00 +1.0\n"
                 "  - label: one\n  # why this card is here\n  - detail: two\n")
    assert entry["label"] == "one"
    assert entry["detail"] == "two"


def test_an_act_default_never_overrides_a_card_s_own_kind():
    """Most rows in a chapter file are chat; a status card still is not."""
    entry = _one("---\nact: X\ndefaults:\n  kind: chat\n---\n\n"
                 "## 0:00\n\n* status @ 0:00 +1.0\n  - label: hello\n")
    assert entry["kind"] == "status"


def test_an_explicit_null_row_deletes_a_field_the_defaults_supplied():
    """One card opting out of the fades every pill around it carries."""
    entry = _one("---\nact: X\ndefaults:\n  fade_in: 0.6\n---\n\n"
                 "## 0:00\n\n* status @ 0:00 +1.0\n  - fade_in: null\n")
    assert "fade_in" not in entry


def test_derived_fade_out_at_can_be_offset_by_the_act_s_own_number():
    """Some acts start the fade a fade-IN's length early. That is on screen."""
    plain = _one("---\nact: X\ndefaults:\n  fade_out: 0.25\n"
                 "  fade_out_at: derived\n---\n\n"
                 "## 0:00\n\nSomeone @ 0:10 +2.8: hello\n")
    offset = _one("---\nact: X\ndefaults:\n  fade_out: 0.25\n"
                  "  fade_out_at: derived 0.6\n---\n\n"
                  "## 0:00\n\nSomeone @ 0:10 +2.8: hello\n")
    assert plain["fade_out_at"] == 12.55
    assert offset["fade_out_at"] == 12.2


def test_a_speaker_may_be_bracketed_even_after_an_id():
    """Act III's speaker is `[redacted]` -- he is revealed in act VI."""
    entry = _one("## 0:00\n\n[retirement-1] [redacted] @ 0:03.567 +2.125: "
                 "Finally, retirement\n")
    assert entry["id"] == "retirement-1"
    assert entry["speaker"] == "[redacted]"
    assert entry["text"] == "Finally, retirement"


def test_an_untimed_chapter_invents_no_clock_and_no_id():
    """Act VIII's credit cards are weights, and are addressed by order."""
    text = ("---\nact: X\ntimed: false\nlist_keys:\n---\n\n"
            "## the cries\n\n* cta\n  - text: FIGHT\n  - dur_sec: 9.5\n")
    entries, _ = chapter_md.untimed_entries(
        "X", chapter_md.parse(text), {}, None)
    assert entries == [{"kind": "cta", "text": "FIGHT", "dur_sec": 9.5}]


def test_a_kindless_card_carries_no_kind_field():
    """Act VIII's fixed credits are told apart by role and never had one."""
    entry = _one("## 0:00\n\n* - @ 0:00 +1.0\n  - role: Music by\n")
    assert "kind" not in entry
    assert entry["role"] == "Music by"


def test_which_keys_are_lists_is_a_fact_about_the_act():
    """The prologue's `body` is a page of lines; act VIII's is a sentence."""
    listed = _one("---\nact: X\nlist_keys: body\n---\n\n"
                  "## 0:00\n\n* thing @ 0:00 +1.0\n  - body: one line\n")
    scalar = _one("---\nact: X\nlist_keys:\n---\n\n"
                  "## 0:00\n\n* thing @ 0:00 +1.0\n  - body: one line\n")
    assert listed["body"] == ["one line"]
    assert scalar["body"] == "one line"


def test_a_float_field_does_not_come_back_as_an_int():
    """`4.0` rewritten as `4` is a delivered record changed for nothing."""
    assert chapter_md._num(4.0) == "4.0"
    assert chapter_md._num(4) == "4"
    assert chapter_md._num(2.4) == "2.4"


def test_a_chapter_that_resolves_to_nothing_says_so():
    """Silence used to look exactly like perfect agreement."""
    notes = chapter_md._check_in_order([], [{"text": "a"}, {"text": "b"}])
    assert notes and "0 card(s)" in notes[0]


def test_a_derived_nameplate_is_carried_through_a_sync_untouched():
    """A chapter file owns its words, not the whole array around them."""
    before = [{"id": "plate", "copy_source": "brief", "name": "Someone Real"},
              {"id": "pill", "text": "old"}]
    merged, notes = chapter_md._merge_plates(
        before, [{"id": "pill", "text": "new"}])
    assert merged == [before[0], {"id": "pill", "text": "new"}]
    assert notes == []


def test_an_unauthored_non_derived_plate_is_dropped_with_a_note():
    """Carrying it through made deletion inexpressible -- act III's
    retirement pair survived its 2026-08-24 move to act II until this."""
    before = [{"id": "plate", "copy_source": "casting", "name": "Trustee"},
              {"id": "gone", "copy_source": "owner_supplied", "text": "x"},
              {"id": "pill", "text": "old"}]
    merged, notes = chapter_md._merge_plates(
        before, [{"id": "pill", "text": "new"}])
    assert merged == [before[0], {"id": "pill", "text": "new"}]
    assert notes and "gone" in notes[0] and "dropped" in notes[0]


# ---------------------------------------------------------------------------
# The two portrait keys, from act II's migration.
# ---------------------------------------------------------------------------

def test_avatar_login_takes_that_accounts_github_picture():
    entry = _one("## 0:00\n\nkylegospo @ 0:00 +2.2: Sup\n"
                 "  - avatar_login: KyleGospo\n")
    assert entry["avatar"] == "renders/avatars/KyleGospo.png"
    assert entry["avatar_url"] == \
        "https://github.com/KyleGospo.png?size=256"
    assert "avatar_login" not in entry, \
        "an authoring key reached the manifest"


def test_cast_takes_the_portrait_the_casting_vocab_records():
    entry = _one("## 0:00\n\nJoseph @ 0:00 +2.2: Is it worth it?\n"
                 "  - cast: joseph_sandoval\n")
    assert entry["avatar"] == "renders/avatars/joseph_sandoval.png"
    assert entry["avatar_url"] == \
        chapter_md._casting_avatars()["joseph_sandoval"]
    assert "cast" not in entry


def test_naming_somebody_with_no_recorded_portrait_draws_the_crest():
    """An answer, not a gap: the pill keeps its crest rather than a made-up
    URL for a person whose picture nobody has recorded."""
    entry = _one("## 0:00\n\nkarena @ 0:00 +2.2: I love this job\n"
                 "  - cast: nobody_has_this_key\n")
    assert "avatar" not in entry and "avatar_url" not in entry


def test_a_speaker_who_is_a_login_still_needs_no_portrait_row():
    entry = _one("## 0:00\n\nkylegospo @ 0:00 +2.2: Sup\n")
    assert entry["avatar_url"] == "https://github.com/kylegospo.png?size=256"


def test_the_two_portrait_keys_are_not_interchangeable():
    """Collapsing them would swap faces on eight delivered pills."""
    by_cast = _one("## 0:00\n\nA1RM4X @ 0:00 +2.2: hi\n  - cast: a1rm4x\n")
    by_login = _one("## 0:00\n\nA1RM4X @ 0:00 +2.2: hi\n"
                    "  - avatar_login: A1RM4X\n")
    assert by_login["avatar_url"] == "https://github.com/A1RM4X.png?size=256"
    if "avatar_url" in by_cast:
        assert by_cast["avatar_url"] != by_login["avatar_url"]


# --- decks: copy that plays AFTER the act, authored inside it ---------------

DECK_MD = """---
act: ZZ
programme_start: 100.0
deck: intermission
defaults:
  copy_source: owner_supplied
---

## 1:41.000
someone: A line that belongs to the act itself

## 1:50.000 intermission
* [slide-1] slide @ 1:50.000 +6.0
  - label: FIRST
* [slide-2] slide @ 1:56.800 +6.0
  - label: SECOND
"""


def _wire(tmp_path, monkeypatch, text=DECK_MD, name="ZZ-deck.md"):
    (tmp_path / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(chapter_md, "CHAPTERS_DIR", tmp_path)


def test_a_labelled_block_leaves_the_act_and_becomes_a_deck(tmp_path, monkeypatch):
    """`deck: <label>` in the front matter is the boundary. It is written
    down where the copy is, rather than inferred from the act's runtime --
    act III's manifest has no film_sec at all."""
    _wire(tmp_path, monkeypatch)
    act, _ = chapter_md.entries("ZZ")
    deck, _ = chapter_md.deck_entries("ZZ")
    assert [e.get("speaker") for e in act] == ["someone"]
    assert [e["id"] for e in deck] == ["slide-1", "slide-2"]


def test_a_deck_comes_back_rebased_to_its_own_clock(tmp_path, monkeypatch):
    """A deck renders as its own film, so its first slide starts at 0 --
    not at wherever it sits in the act's or the programme's clock."""
    _wire(tmp_path, monkeypatch)
    deck, _ = chapter_md.deck_entries("ZZ")
    assert deck[0]["at"] == pytest.approx(0.0)
    assert deck[1]["at"] == pytest.approx(6.8)


def test_an_act_with_no_deck_key_keeps_every_block(tmp_path, monkeypatch):
    """The label is only a boundary when the front matter names it. A file
    that says nothing about decks behaves exactly as it always did."""
    _wire(tmp_path, monkeypatch,
          DECK_MD.replace("deck: intermission\n", ""))
    act, _ = chapter_md.entries("ZZ")
    deck, _ = chapter_md.deck_entries("ZZ")
    assert len(act) == 3 and deck == []


def test_act_iii_authors_its_intermission_at_the_end_of_its_own_file():
    """The owner's arrangement, verbatim: 'Have it be the concluding text of
    his scene so I can edit it in one place.'"""
    act, _ = chapter_md.entries("III")
    deck, _ = chapter_md.deck_entries("III")
    assert [e["id"] for e in deck] == [f"intermission-{n}" for n in (1, 2, 3, 4)]
    assert not [e for e in act if e["id"].startswith("intermission")]
    assert deck[0]["at"] == pytest.approx(0.0)
    assert all(e["position"] == "slide" for e in deck)


# --- writing the way the owner writes ---------------------------------------

def _lines(md):
    blocks = chapter_md.parse("## 1:00\n" + md)
    return [(e.get("speaker"), e.get("text")) for e in blocks[0]["lines"]]


def test_a_line_under_a_pill_is_the_next_line_of_the_conversation():
    """REGRESSION: about twenty authored lines existed only as text in a
    file. A continuation was dropped in silence."""
    assert _lines("kat: The gamers would have to impress\nBOTH Ricardos\n") == [
        ("kat", "The gamers would have to impress"),
        ("kat", "BOTH Ricardos"),
    ]


def test_a_continuation_chain_keeps_going():
    got = _lines("kat: one\ntwo\nthree\n")
    assert got == [("kat", "one"), ("kat", "two"), ("kat", "three")]


def test_an_indented_line_under_a_pill_is_the_next_line():
    """Owner, 2026-08-23: "if there is an indent under a pill make it a new
    line". He writes a continuation both flush-left and indented, so the
    grammar reads both; a rule that keyed on indentation would drop half of
    them in silence, which is the failure this replaces."""
    assert _lines("kat: one\n    and the rest of it\n") == [
        ("kat", "one"), ("kat", "and the rest of it")]


def test_an_indented_note_a_blank_line_later_is_still_a_note():
    """Dozens of existing notes are indented, and every one of them is
    separated from its pill by a blank line. ADJACENCY, not indentation, is
    what keeps them off the screen."""
    assert _lines("kat: one\n\n    Owner brief: this is commentary\n") == [
        ("kat", "one")]


def test_a_paragraph_a_blank_line_later_is_prose_not_speech():
    """Adjacency is what separates 'still talking' from 'writing about the
    act'."""
    assert _lines("kat: one\n\nThis paragraph explains the act\n") == [
        ("kat", "one")]


def test_a_bracketed_name_is_a_speaker():
    assert _lines("[amber] Which one of you is Kyleford?\n") == [
        ("amber", "Which one of you is Kyleford?")]


def test_a_bracketed_name_takes_a_pin_and_a_hold():
    blocks = chapter_md.parse("## 1:00\n[amber] @ 1:02.5 +3.0: Hi\n")
    entry, = blocks[0]["lines"]
    assert (entry["speaker"], entry["pin"], entry["hold"], entry["text"]) == (
        "amber", 62.5, 3.0, "Hi")


def test_a_bracketed_id_is_still_an_id_not_a_speaker():
    """`[an_id] speaker: words` must keep working -- every migrated act is
    written that way."""
    blocks = chapter_md.parse("## 1:00\n[the_id] kat @ 1:02 +2.0: words\n")
    entry, = blocks[0]["lines"]
    assert entry["id"] == "the_id" and entry["speaker"] == "kat"


def test_a_github_url_in_the_brackets_names_the_person_not_the_url():
    """A URL points AT somebody. Putting it on screen is the bug."""
    blocks = chapter_md.parse(
        "## 1:00\n[https://github.com/wrkode] Oh dibs on this one\n")
    entry, = blocks[0]["lines"]
    assert entry["speaker"] == "wrkode"
    assert entry["attrs"]["avatar_login"] == "wrkode"
    assert "github.com" not in entry["text"]


def test_an_agent_note_never_reaches_the_screen():
    """REGRESSION: 'Add youtube click link thing to this video...' was a
    pill on screen with a blank speaker, because it ended in a colon."""
    assert _lines(
        "kat: one\n>> Add youtube click link thing to this video: <<\n") == [
        ("kat", "one")]


def test_an_agent_note_can_span_lines_and_does_not_detach_the_rows_below():
    blocks = chapter_md.parse(
        "## 1:00\n* [c] card\n>> think about\nthis later <<\n  - label: KEPT\n")
    entry, = blocks[0]["lines"]
    assert entry["attrs"]["label"] == "KEPT"


def test_a_note_between_two_pills_does_not_glue_them_together():
    assert _lines("kat: one\n>> a note <<\ntwo\n") == [
        ("kat", "one"), ("kat", "two")]
