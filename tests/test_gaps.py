import json

from tools.gaps import (
    FINGERPRINT_PREFIX,
    covered_by_human_issue,
    file_gaps,
    find_gaps,
    fingerprint_of,
    format_report,
    issue_body,
)


def _video(tmp_path, video_id, **extra):
    directory = tmp_path / "videos"
    directory.mkdir(exist_ok=True)
    record = {
        "video_id": video_id,
        "youtube_url": f"https://youtu.be/{video_id}",
        "title": video_id,
        "era": "unknown",
        "activity": "cinematic",
        "content_type": "cinematic",
        "usage_class": "third_party_copyrighted",
        "source_rights_note": "fan content",
    }
    record.update(extra)
    (directory / f"{video_id}.json").write_text(json.dumps(record))
    return directory


def _segment(tmp_path, video_id, index, **extra):
    directory = tmp_path / "segments"
    directory.mkdir(exist_ok=True)
    record = {
        "segment_id": f"seg_{video_id}_{index}",
        "video_id": video_id,
        "start_sec": index,
        "end_sec": index + 1,
        "subject_salience": "environment",
    }
    record.update(extra)
    (directory / f"{record['segment_id']}.json").write_text(json.dumps(record))
    return directory


def test_an_ingested_video_with_no_segments_is_a_gap(tmp_path):
    videos = _video(tmp_path, "yt_never_indexed")
    segments = tmp_path / "segments"
    segments.mkdir()
    gaps = find_gaps(videos, segments)
    unindexed = [g for g in gaps if g["kind"] == "unindexed"]
    assert [g["video_id"] for g in unindexed] == ["yt_never_indexed"]


def test_a_correctly_rejected_beat_is_not_a_gap(tmp_path):
    # burned_text is the gate working, not work remaining.
    videos = _video(tmp_path, "yt_v")
    _segment(tmp_path, "yt_v", 0, overlays=["burned_text"], clean=False,
             character=[{"name": "Osiris"}])
    segments = _segment(tmp_path, "yt_v", 1, overlays=[], clean=True,
                        character=[{"name": "Osiris"}])
    assert [g for g in find_gaps(videos, segments) if g["kind"] == "unreviewed"] == []


def test_an_untagged_beat_is_a_gap(tmp_path):
    videos = _video(tmp_path, "yt_v")
    _segment(tmp_path, "yt_v", 0, clean=False, character=[{"name": "Osiris"}])
    segments = _segment(tmp_path, "yt_v", 1, overlays=[], clean=True,
                        character=[{"name": "Osiris"}])
    gaps = [g for g in find_gaps(videos, segments) if g["kind"] == "unreviewed"]
    assert gaps[0]["counts"] == {"segments": 2, "unreviewed": 1}


def test_an_indexed_video_naming_nobody_is_a_gap(tmp_path):
    videos = _video(tmp_path, "yt_v")
    segments = _segment(tmp_path, "yt_v", 0, overlays=[], clean=True)
    kinds = [g["kind"] for g in find_gaps(videos, segments)]
    assert "untagged-character" in kinds


def test_uncast_leads_are_reported_from_the_real_vocab(tmp_path):
    videos = tmp_path / "videos"
    videos.mkdir()
    segments = tmp_path / "segments"
    segments.mkdir()
    uncast = [g for g in find_gaps(videos, segments) if g["kind"] == "uncast"]
    assert uncast and uncast[0]["counts"]["uncast"] > 0
    assert "the_witness" in uncast[0]["detail"]


def test_casting_a_lead_is_never_called_automatable(tmp_path):
    videos = tmp_path / "videos"
    videos.mkdir()
    segments = tmp_path / "segments"
    segments.mkdir()
    uncast = [g for g in find_gaps(videos, segments) if g["kind"] == "uncast"][0]
    assert uncast["automatable"] == "no"


def test_fingerprints_are_stable_when_the_numbers_move(tmp_path):
    videos = _video(tmp_path, "yt_v")
    _segment(tmp_path, "yt_v", 0, clean=False)
    segments = _segment(tmp_path, "yt_v", 1, clean=False)
    first = [g for g in find_gaps(videos, segments) if g["kind"] == "unreviewed"][0]

    _segment(tmp_path, "yt_v", 2, clean=False)
    second = [g for g in find_gaps(videos, segments) if g["kind"] == "unreviewed"][0]

    assert first["counts"] != second["counts"]
    assert first["fingerprint"] == second["fingerprint"]


def test_a_filed_issue_carries_its_fingerprint():
    gap = {"kind": "unindexed", "fingerprint": "unindexed:yt_v", "video_id": "yt_v",
           "title": "t", "detail": "d", "counts": {}, "automatable": "partly"}
    body = issue_body(gap)
    assert FINGERPRINT_PREFIX in body
    assert fingerprint_of(body) == "unindexed:yt_v"
    assert "**Automatable:** partly" in body


def test_a_rerun_updates_instead_of_duplicating():
    gap = {"kind": "unindexed", "fingerprint": "unindexed:yt_v", "video_id": "yt_v",
           "title": "yt_v is ingested but not indexed", "detail": "d",
           "counts": {}, "automatable": "partly"}
    existing = [{"number": 12, "title": "old title",
                 "body": f"<!-- {FINGERPRINT_PREFIX} unindexed:yt_v -->"}]
    actions = file_gaps([gap], existing, dry_run=True)
    assert actions == ["update #12: yt_v is ingested but not indexed"]


def test_a_gap_a_human_already_filed_is_left_alone():
    # Issue #7 is the real case: a person described this exact gap in their own
    # words, and a robot copy beside it would bury the version being worked from.
    gap = {"kind": "unreviewed", "fingerprint": "unreviewed:yt_season_of_the_lost",
           "video_id": "yt_season_of_the_lost", "title": "t", "detail": "d",
           "counts": {}, "automatable": "partly"}
    human = [{"number": 7,
              "title": "Season of the Lost: 61 of 73 beats still unreviewed",
              "body": "`yt_season_of_the_lost` is indexed with 73 beats."}]
    assert covered_by_human_issue(gap, human) is True
    assert file_gaps([gap], human, dry_run=True) == [
        "skip (a human already filed it): t"
    ]


def test_a_robot_issue_does_not_count_as_human_coverage():
    gap = {"kind": "unreviewed", "fingerprint": "unreviewed:yt_v", "video_id": "yt_v",
           "title": "t", "detail": "d", "counts": {}, "automatable": "partly"}
    robot = [{"number": 9, "title": "yt_v something",
              "body": f"<!-- {FINGERPRINT_PREFIX} unreviewed:yt_v -->"}]
    assert covered_by_human_issue(gap, robot) is False


def test_report_is_empty_when_nothing_is_missing():
    assert "no gaps" in format_report([])


def test_every_unreviewed_beat_in_the_real_index_is_reported():
    # A long archive is reviewed incrementally, so an unreviewed beat is a
    # normal state, not a fault -- what matters is that it is *visible*. This
    # used to assert the index was finished, which quietly turned "somebody is
    # still reviewing the Season of the Lost archive" into a test failure. The
    # invariant worth keeping is the reporting one: every video holding an
    # untagged beat surfaces as a gap somebody can pick up.
    import glob
    import json
    from pathlib import Path

    reported = {g["video_id"] for g in find_gaps() if g["kind"] == "unreviewed"}

    holding = set()
    for path in glob.glob(str(Path(__file__).resolve().parents[1] / "tags" / "*.json")):
        tags = json.loads(Path(path).read_text())
        if any("overlays" not in beat for beat in tags.values()):
            holding.add(Path(path).stem)

    assert holding <= reported, (
        f"videos with untagged beats that no gap reports: {sorted(holding - reported)}. "
        "An unreviewed beat that nobody can see is how a half-indexed video "
        "gets forgotten."
    )


def test_a_record_with_no_real_url_is_not_reported_as_a_gap(tmp_path):
    # The README's offline ingest example leaves videos/yt_demo.json behind,
    # with youtube_url https://youtu.be/unknown. There is no video to fetch, so
    # filing it would mean an issue nobody can close.
    videos = _video(tmp_path, "yt_demo", youtube_url="https://youtu.be/unknown")
    segments = tmp_path / "segments"
    segments.mkdir()
    assert [g for g in find_gaps(videos, segments) if g["kind"] == "unindexed"] == []


def test_a_record_with_a_real_url_still_is(tmp_path):
    videos = _video(tmp_path, "yt_real", youtube_url="https://www.youtube.com/watch?v=abc")
    segments = tmp_path / "segments"
    segments.mkdir()
    gaps = [g for g in find_gaps(videos, segments) if g["kind"] == "unindexed"]
    assert [g["video_id"] for g in gaps] == ["yt_real"]


def test_a_nested_video_id_does_not_silence_another_videos_gaps():
    # yt_a_reveal contains yt_a; a substring match would let a human issue
    # about one video hide every gap of the other.
    gap = {"kind": "unindexed", "fingerprint": "unindexed:yt_a", "video_id": "yt_a",
           "title": "t", "detail": "d", "counts": {}, "automatable": "partly"}
    human = [{"number": 3, "title": "about yt_a_reveal", "body": "yt_a_reveal is fine"}]
    assert covered_by_human_issue(gap, human) is False


def test_the_video_id_still_matches_inside_backticks_and_prose():
    gap = {"kind": "unreviewed", "fingerprint": "unreviewed:yt_a", "video_id": "yt_a",
           "title": "t", "detail": "d", "counts": {}, "automatable": "partly"}
    human = [{"number": 3, "title": "beats unreviewed",
              "body": "`yt_a` is indexed with 73 beats."}]
    assert covered_by_human_issue(gap, human) is True
