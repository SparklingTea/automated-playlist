"""Resolves a parsed SongQuery to the best-matching Spotify track, if any."""
from dataclasses import dataclass

from rapidfuzz import fuzz

from playlist_builder.parser import SongQuery
from playlist_builder.spotify_client import SpotifyClient

MATCH_THRESHOLD = 70
# Good enough that the remaining queries/variants can't meaningfully improve
# on it, so skip them rather than spend more API calls.
CONFIDENT_SCORE = 90


@dataclass
class MatchResult:
    query: SongQuery
    track: dict | None
    score: float


def _build_search_queries(title: str | None, artist: str | None) -> list[str]:
    if title and artist:
        return [f'track:"{title}" artist:"{artist}"', f"{title} {artist}"]
    if title:
        return [title]
    return []


def _score(title: str | None, artist: str | None, track: dict) -> float:
    track_name = track["name"]
    track_artists = ", ".join(a["name"] for a in track["artists"])
    name_score = fuzz.token_set_ratio(title or "", track_name)
    if artist:
        artist_score = fuzz.token_set_ratio(artist, track_artists)
        return (name_score + artist_score) / 2
    return name_score


def find_best_match(client: SpotifyClient, query: SongQuery) -> MatchResult:
    best_track = None
    best_score = 0.0

    for title, artist in query.query_variants():
        for search_query in _build_search_queries(title, artist):
            for track in client.search_tracks(search_query, limit=5):
                score = _score(title, artist, track)
                if score > best_score:
                    best_score = score
                    best_track = track
            if best_score >= CONFIDENT_SCORE:
                return MatchResult(query=query, track=best_track, score=best_score)

    if best_track and best_score >= MATCH_THRESHOLD:
        return MatchResult(query=query, track=best_track, score=best_score)
    return MatchResult(query=query, track=None, score=best_score)
