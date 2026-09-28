"""Thin wrapper around spotipy for the operations this tool needs."""
import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

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


class SpotifyClient:
    def __init__(self, auth_manager: SpotifyOAuth | None = None):
        self._sp = spotipy.Spotify(auth_manager=auth_manager or build_auth_manager())

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
