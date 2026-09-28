from unittest.mock import Mock, patch

from playlist_builder.sources.website_source import fetch_song_lines

NAV = "<nav><ul>" + "".join(f"<li>Menu {i}</li>" for i in range(10)) + "</ul></nav>"


def _fetch(html: str) -> list[str]:
    response = Mock(content=html.encode("utf-8"))
    with patch("playlist_builder.sources.website_source.requests.get", return_value=response):
        return fetch_song_lines("https://example.com").splitlines()


def test_keeps_only_song_lines_from_article_text():
    songs = [f"Song {i}, Artist {i}, 19{80 + i}" for i in range(6)]
    html = (
        f"<html><body>{NAV}<main><h2>Reggae</h2><p>Intro prose here.</p>"
        + "".join(f"<p>{s}</p>" for s in songs)
        + "</main><footer><li>Contact</li><li>Press</li><li>Shop</li></footer></body></html>"
    )
    assert _fetch(html) == songs


def test_falls_back_to_list_items_without_song_separators():
    html = f"<html><body>{NAV}<main><ol><li>Karma Police</li><li>No Surprises</li><li>Creep</li></ol></main></body></html>"
    assert _fetch(html) == ["Karma Police", "No Surprises", "Creep"]
