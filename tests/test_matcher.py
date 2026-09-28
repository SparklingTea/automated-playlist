from playlist_builder.matcher import MATCH_THRESHOLD, find_best_match
from playlist_builder.parser import parse_lines


class FakeSpotifyClient:
    """Returns canned results for any query containing one of the given keys."""

    def __init__(self, responses: dict):
        self._responses = responses

    def search_tracks(self, query: str, limit: int = 5) -> list:
        for key, tracks in self._responses.items():
            if key.lower() in query.lower():
                return tracks
        return []


def _track(name, artist, uri):
    return {"name": name, "artists": [{"name": artist}], "uri": uri}


def test_picks_the_variant_that_actually_matches():
    # Raw line orders it as "Radiohead - Karma Police", i.e. title/artist
    # backwards relative to the real track; the matcher must try the swap.
    [query] = parse_lines("Radiohead - Karma Police")
    client = FakeSpotifyClient(
        {"Karma Police": [_track("Karma Police", "Radiohead", "spotify:track:1")]}
    )

    result = find_best_match(client, query)

    assert result.track is not None
    assert result.track["uri"] == "spotify:track:1"
    assert result.score >= MATCH_THRESHOLD


def test_low_similarity_is_skipped():
    [query] = parse_lines("Some Completely Unknown Song")
    client = FakeSpotifyClient(
        {"Some Completely Unknown Song": [_track("Totally Different Track", "Nobody", "spotify:track:2")]}
    )

    result = find_best_match(client, query)

    assert result.track is None
    assert result.score < MATCH_THRESHOLD


def test_no_search_results_is_skipped():
    [query] = parse_lines("Nonexistent Song")
    client = FakeSpotifyClient({})

    result = find_best_match(client, query)

    assert result.track is None
    assert result.score == 0.0
