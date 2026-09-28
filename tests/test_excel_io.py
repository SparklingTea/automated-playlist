import io

import pytest
from openpyxl import Workbook

from playlist_builder.excel_io import ExcelFormatError, from_excel, to_excel_bytes
from playlist_builder.parser import parse_lines

TRACK_ID = "4u7EnebtmKWzUH433cf5Qv"


def _track(name, artists, track_id=TRACK_ID):
    return {"name": name, "artists": [{"name": a} for a in artists], "uri": f"spotify:track:{track_id}"}


def _sheet(*rows) -> io.BytesIO:
    wb = Workbook()
    for row in rows:
        wb.active.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_round_trip_keeps_matches_and_skips():
    [q1] = parse_lines("Queen - Bohemian Rhapsody")
    [q2] = parse_lines("Some Obscure Song")
    exported = to_excel_bytes([(q1, _track("Bohemian Rhapsody", ["Queen", "Freddie Mercury"])), (q2, None)])

    (r1, t1), (r2, t2) = from_excel(io.BytesIO(exported))
    assert r1.raw_line == "Queen - Bohemian Rhapsody"
    assert t1 == _track("Bohemian Rhapsody", ["Queen", "Freddie Mercury"])
    assert r2.raw_line == "Some Obscure Song" and t2 is None


def test_accepts_links_only_and_hand_filled_rows():
    sheet = _sheet(
        ["Title", "Artist", "Spotify link"],
        ["Karma Police", "Radiohead", f"https://open.spotify.com/intl-de/track/{TRACK_ID}?si=abc"],
        ["No Link Yet", "Someone", None],
        [None, None, None],
    )
    (q1, t1), (q2, t2) = from_excel(sheet)
    assert t1["uri"] == f"spotify:track:{TRACK_ID}"
    assert q1.raw_line == "Karma Police - Radiohead"
    assert q2.raw_line == "No Link Yet - Someone" and t2 is None


def test_missing_uri_column_is_rejected():
    with pytest.raises(ExcelFormatError):
        from_excel(_sheet(["Title", "Artist"], ["Karma Police", "Radiohead"]))
