"""Streamlit UI: build a Spotify playlist from a web page or a screenshot."""
import pytesseract
import requests
import streamlit as st
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.exceptions import SpotifyException

from playlist_builder.config import ConfigError
from playlist_builder.excel_io import ExcelFormatError, from_excel, to_excel_bytes
from playlist_builder.matcher import find_best_match
from playlist_builder.parser import parse_lines
from playlist_builder.sources import image_source, website_source
from playlist_builder.spotify_client import SpotifyClient, build_auth_manager

st.set_page_config(page_title="Playlist Builder", page_icon="🎵")
st.title("🎵 Playlist Builder")
st.caption("Turn a playlist web page or screenshot into a Spotify playlist.")

state = st.session_state
state.setdefault("raw_text", "")
state.setdefault("matches", None)
# Per-session token so each visitor uses their own Spotify account.
state.setdefault("token_cache", MemoryCacheHandler())

@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=20000)
def _cached_search(_client: SpotifyClient, query: str, limit: int) -> list[dict]:
    return _client.search_tracks(query, limit=limit)


class CachedSearchClient:
    """Catalog search results aren't user-specific, so re-matching an edited
    list (or the same list by another visitor) only searches new lines."""

    def __init__(self, client: SpotifyClient):
        self._client = client

    def search_tracks(self, query: str, limit: int = 5) -> list[dict]:
        return _cached_search(self._client, query, limit)


# --- Spotify login ---------------------------------------------------------
try:
    auth = build_auth_manager(cache_handler=state.token_cache, open_browser=False)
except ConfigError as e:
    st.error(str(e))
    st.stop()

if "code" in st.query_params:
    try:
        auth.get_access_token(st.query_params["code"], as_dict=False, check_cache=False)
    except Exception as e:
        st.error(f"Spotify login failed: {e}")
    st.query_params.clear()

if not auth.validate_token(state.token_cache.get_cached_token()):
    st.info("Log in with Spotify to get started. The login opens in a new tab; continue there afterwards.")
    st.link_button("Log in with Spotify", auth.get_authorize_url(), type="primary")
    st.stop()

client = SpotifyClient(auth_manager=auth, wait_on_rate_limit=False)
if "user_name" not in state:
    try:
        state.user_name = client.current_user_name()
    except SpotifyException:
        state.user_name = "your Spotify account"
with st.sidebar:
    st.write(f"Logged in as **{state.user_name}**")
    if st.button("Log out"):
        state.token_cache = MemoryCacheHandler()
        del state.user_name
        st.rerun()


# --- Step 1: input ---------------------------------------------------------
st.subheader("1. Choose a source")
website_tab, image_tab, excel_tab = st.tabs(["🌐 Website", "🖼️ Screenshot", "📊 Excel"])

with website_tab:
    url = st.text_input("Playlist page URL", placeholder="https://example.com/best-songs-of-2025")
    if st.button("Extract songs from page", disabled=not url):
        try:
            with st.spinner("Fetching page..."):
                state.raw_text = website_source.fetch_song_lines(url)
            state.matches = None
        except requests.RequestException as e:
            st.error(f"Couldn't fetch the page: {e}")

with image_tab:
    upload = st.file_uploader("Screenshot or photo of a playlist", type=["png", "jpg", "jpeg", "webp", "bmp"])
    if upload:
        st.image(upload, width="stretch")
    if st.button("Extract songs from image", disabled=upload is None):
        try:
            with st.spinner("Reading text from image..."):
                state.raw_text = image_source.extract_text(upload)
            state.matches = None
        except pytesseract.TesseractNotFoundError:
            st.error(
                "Tesseract OCR isn't installed. Install it from "
                "https://github.com/UB-Mannheim/tesseract/wiki and add it to PATH, "
                "or set TESSERACT_CMD in .env to the full path of tesseract.exe."
            )

with excel_tab:
    st.caption("Upload a list exported from this app (or any sheet with a 'Spotify URI' or 'Spotify link' column) to skip matching.")
    excel = st.file_uploader("Excel file", type=["xlsx"])
    if st.button("Load playlist from Excel", disabled=excel is None):
        try:
            state.matches = from_excel(excel)
            state.raw_text = ""
        except ExcelFormatError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Couldn't read that file as Excel: {e}")

# --- Step 2: review --------------------------------------------------------
if state.raw_text:
    st.subheader("2. Review the song list")
    st.caption("One song per line. Delete junk lines or fix OCR mistakes before matching.")
    st.text_area("Songs", key="raw_text", height=250, label_visibility="collapsed")
    queries = parse_lines(state.raw_text)
    st.write(f"**{len(queries)}** entries detected.")

    if st.button("Match on Spotify", type="primary", disabled=not queries):
        search_client = CachedSearchClient(client)
        progress = st.progress(0.0, text="Searching Spotify...")
        matches = []
        try:
            for i, query in enumerate(queries, 1):
                matches.append((query, find_best_match(search_client, query).track))
                progress.progress(i / len(queries), text=f"Searching Spotify... {i}/{len(queries)}")
        except SpotifyException as e:
            if e.http_status != 429:
                raise
            wait = int((e.headers or {}).get("Retry-After", 0) or 0)
            st.warning(
                f"Spotify's rate limit stopped matching after {len(matches)} of {len(queries)} songs"
                + (f"; it asks to wait about {max(1, round(wait / 60))} min" if wait else "")
                + ". Click **Match on Spotify** again after that: songs already searched are cached and won't count again."
            )
        progress.empty()
        state.matches = matches

# --- Step 3: results & create ----------------------------------------------
if not state.matches:
    st.stop()

st.subheader("3. Matches")
found = [(q, t) for q, t in state.matches if t]
skipped = [q for q, t in state.matches if not t]
st.write(f"✅ **{len(found)}** found · ⏭️ **{len(skipped)}** skipped")

st.dataframe(
    [
        {
            "Input": q.raw_line,
            "Spotify match": f"{t['name']} — {', '.join(a['name'] for a in t['artists'])}" if t else "—",
        }
        for q, t in state.matches
    ],
    width="stretch",
    hide_index=True,
)

st.download_button(
    "⬇️ Download as Excel",
    data=to_excel_bytes(state.matches),
    file_name="playlist.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Re-import this file from the Excel tab to skip matching next time. Skipped rows can be filled in by hand.",
)

if found:
    with st.form("create"):
        name = st.text_input("Playlist name", value="My Playlist")
        description = st.text_input("Description (optional)")
        public = st.checkbox("Public playlist")
        if st.form_submit_button("Create playlist on Spotify", type="primary"):
            playlist = client.create_playlist(name, public=public, description=description)
            client.add_tracks(playlist["id"], [t["uri"] for _, t in found])
            st.success(f"Created playlist with {len(found)} tracks: {playlist['external_urls']['spotify']}")
