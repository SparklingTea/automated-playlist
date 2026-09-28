from playlist_builder.parser import parse_lines


def test_dash_separator_produces_both_orderings():
    [query] = parse_lines("Radiohead - Karma Police")
    assert query.title == "Radiohead"
    assert query.artist == "Karma Police"
    assert query.alt_title == "Karma Police"
    assert query.alt_artist == "Radiohead"


def test_en_dash_and_em_dash_supported():
    [q1] = parse_lines("Radiohead – Karma Police")
    [q2] = parse_lines("Radiohead — Karma Police")
    assert q1.title == "Radiohead" and q1.artist == "Karma Police"
    assert q2.title == "Radiohead" and q2.artist == "Karma Police"


def test_by_pattern():
    [query] = parse_lines("Karma Police by Radiohead")
    assert query.title == "Karma Police"
    assert query.artist == "Radiohead"
    assert query.alt_title is None
    assert query.alt_artist is None


def test_plain_line_has_no_artist():
    [query] = parse_lines("Karma Police")
    assert query.title == "Karma Police"
    assert query.artist is None


def test_strips_numbering_bullets_and_quotes():
    text = '1. "Karma Police"\n- Paranoid Android\n* No Surprises\n(3) Fake Plastic Trees'
    queries = parse_lines(text)
    titles = [q.title for q in queries]
    assert titles == ["Karma Police", "Paranoid Android", "No Surprises", "Fake Plastic Trees"]


def test_blank_lines_and_duplicates_are_skipped():
    text = "Karma Police\n\nKarma Police\nkarma police\nParanoid Android"
    queries = parse_lines(text)
    assert len(queries) == 2
    assert queries[0].raw_line == "Karma Police"
    assert queries[1].raw_line == "Paranoid Android"


def test_query_variants_returns_reverse_when_ambiguous():
    [query] = parse_lines("Radiohead - Karma Police")
    variants = query.query_variants()
    assert variants == [("Radiohead", "Karma Police"), ("Karma Police", "Radiohead")]


def test_query_variants_single_when_unambiguous():
    [query] = parse_lines("Karma Police by Radiohead")
    assert query.query_variants() == [("Karma Police", "Radiohead")]


def test_strips_quotes_around_title_with_artist():
    [dash] = parse_lines('"Hey Jude" - The Beatles')
    [by] = parse_lines('“Hey Jude” by The Beatles')
    assert dash.title == "Hey Jude" and dash.artist == "The Beatles"
    assert dash.alt_artist == "Hey Jude"
    assert by.title == "Hey Jude" and by.artist == "The Beatles"
