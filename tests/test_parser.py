from playlist_builder.parser import keep_song_lines, looks_like_song, parse_lines


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


def test_title_artist_year_comma_format():
    [q] = parse_lines("Ghost Town, The Specials, 1981")
    [q2] = parse_lines("Memphis Blues, James Reese Europe's band, 1916/17")
    assert (q.title, q.artist) == ("Ghost Town", "The Specials")
    assert (q.alt_title, q.alt_artist) == ("The Specials", "Ghost Town")
    assert (q2.title, q2.artist) == ("Memphis Blues", "James Reese Europe's band")


def test_comma_without_year_is_not_split():
    [q] = parse_lines("Hello, Goodbye")
    assert q.title == "Hello, Goodbye" and q.artist is None


def test_looks_like_song():
    assert looks_like_song("Ghost Town, The Specials, 1981")
    assert looks_like_song("Radiohead - Karma Police")
    assert looks_like_song("Karma Police by Radiohead")
    assert looks_like_song("1979 - Smashing Pumpkins")
    assert not looks_like_song("Reggae")
    assert not looks_like_song("Closes Sunday, 10 January 2027")
    assert not looks_like_song("Modernity..? 1900 – 1948")


def test_keep_song_lines_drops_headings_and_cut_off_ocr_lines():
    ocr = (
        "19; Pani Hardcastie; 1985\n\n"
        "London Town, Light of the World, 1992\n\n"
        "Somebody Help Me Out, Beggar & Co, 1981\n\n"
        "When You Gonna Learn, Jamiroquai, 1992.\n\n"
        "2-Tone\n\n"
        "On My Radio, The Selecter, 1979\n"
    )
    kept = keep_song_lines(ocr).splitlines()
    assert kept == [
        "London Town, Light of the World, 1992",
        "Somebody Help Me Out, Beggar & Co, 1981",
        "When You Gonna Learn, Jamiroquai, 1992.",
        "On My Radio, The Selecter, 1979",
    ]
    assert parse_lines(kept[2])[0].artist == "Jamiroquai"


def test_keep_song_lines_leaves_plain_lists_alone():
    text = "Karma Police\nNo Surprises\nCreep"
    assert keep_song_lines(text) == text
