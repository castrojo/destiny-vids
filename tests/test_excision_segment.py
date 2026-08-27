from pathlib import Path

from scripts import build_excision


def test_the_builder_uses_the_measured_three_beat_timeline():
    assert build_excision.BEATS == [
        {
            "segment_id": "excision-rally",
            "video_id": "yt_excision_chezvii_4k",
            "start_sec": 40.0,
            "end_sec": 92.5,
            "start_tc": "0:40.000",
            "end_tc": "1:32.500",
            "beat": "The defenders of Sol rally for the last battle",
            "redactions": True,
        },
        {
            "segment_id": "excision-ward-of-dawn",
            "video_id": "yt_excision_nohud_hoople",
            "start_sec": 476.0,
            "end_sec": 496.0,
            "start_tc": "7:56.000",
            "end_tc": "8:16.000",
            "beat": "Saint-14's Ward of Dawn holds the line",
        },
        {
            "segment_id": "excision-unmake-the-witness",
            "video_id": "yt_excision_nohud_hoople",
            "start_sec": 938.0,
            "end_sec": 1018.0,
            "start_tc": "15:38.000",
            "end_tc": "16:58.000",
            "beat": "The fireteam channels the Traveler and unmakes the Witness",
        },
    ]
    assert build_excision.film_duration() == 152.5


def test_the_rally_command_removes_only_the_subtitle_bar(tmp_path):
    beat = build_excision.BEATS[0]
    command = build_excision.clip_command(
        ["ffmpeg"],
        beat,
        Path("/media/yt_excision_chezvii_4k.mp4"),
        tmp_path / "rally.mkv",
    )

    video_filter = command[command.index("-vf") + 1]
    assert "drawbox=x=0:y=936:w=1920:h=144" in video_filter
    assert "between(t,0.000,109.000)" in video_filter
