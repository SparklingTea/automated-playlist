"""Thin wrapper around spotipy for the operations this tool needs."""
import requests
import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth
from urllib3.util.retry import Retry

from playlist_builder.config import get_spotify_credentials

SCOPE = "playlist-modify-private playlist-modify-public"
BATCH_SIZE = 100  # Spotify API limit per playlist_add_items call


def build_auth_manager(cache_handler: CacheHandler | None = None, open_browser: bool = True) -> SpotifyOAuth:
    creds = get_spotify_credentials()
    cache_kwargs = {"cache_handler": cache_handler} if cache_handler else {"cache_path": ".spotify_cache"}
    return SpotifyOAuth(
        client_id=creds["SPOTIPY_CLIENT_ID"],
        client_secret=creds["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=creds["SPOTIPY_REDIRECT_URI"],
        scope=SCOPE,
        open_browser=open_browser,
        **cache_kwargs,
    )


def _session_failing_fast_on_429() -> requests.Session:
    # spotipy's default session sleeps for the full Retry-After on a 429,
    # which can be hours after a burst. urllib3 retries any 429 carrying
    # Retry-After regardless of status_forcelist, so it has to be disabled here.
    retry = Retry(
        total=3,
        read=False,
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE"]),
        status=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
        respect_retry_after_header=False,
    )
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class SpotifyClient:
    def __init__(self, auth_manager: SpotifyOAuth | None = None, wait_on_rate_limit: bool = True):
        self._sp = spotipy.Spotify(
            auth_manager=auth_manager or build_auth_manager(),
            requests_session=True if wait_on_rate_limit else _session_failing_fast_on_429(),
        )

    def search_tracks(self, query: str, limit: int = 5) -> list[dict]:
        results = self._sp.search(q=query, type="track", limit=limit)
        return results.get("tracks", {}).get("items", [])

    def current_user_id(self) -> str:
        return self._sp.current_user()["id"]

    def current_user_name(self) -> str:
        user = self._sp.current_user()
        return user.get("display_name") or user["id"]

    def create_playlist(self, name: str, public: bool = False, description: str = "") -> dict:
        # POST /users/{id}/playlists returns 403 for dev-mode apps since Spotify's Feb 2026 API change.
        return self._sp.current_user_playlist_create(name, public=public, description=description)

    def add_tracks(self, playlist_id: str, track_uris: list[str]) -> None:
        for i in range(0, len(track_uris), BATCH_SIZE):
            batch = track_uris[i : i + BATCH_SIZE]
            self._sp.playlist_add_items(playlist_id, batch)
