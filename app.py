"""Streamlit UI: build a Spotify playlist from a web page or a screenshot."""
import pytesseract
import requests
import streamlit as st
from spotipy.cache_handler import MemoryCacheHandler

from playlist_builder.config import ConfigError
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

client = SpotifyClient(auth_manager=auth)
with st.sidebar:
    st.write(f"Logged in as **{client.current_user_name()}**")
    if st.button("Log out"):
        state.token_cache = MemoryCacheHandler()
        st.rerun()


# --- Step 1: input ---------------------------------------------------------
st.subheader("1. Choose a source")
website_tab, image_tab = st.tabs(["🌐 Website", "🖼️ Screenshot"])

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
        st.image(upload, use_container_width=True)
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

# --- Step 2: review --------------------------------------------------------
if not state.raw_text:
    st.stop()

st.subheader("2. Review the song list")
st.caption("One song per line. Delete junk lines or fix OCR mistakes before matching.")
st.text_area("Songs", key="raw_text", height=250, label_visibility="collapsed")
queries = parse_lines(state.raw_text)
st.write(f"**{len(queries)}** entries detected.")

if st.button("Match on Spotify", type="primary", disabled=not queries):
    progress = st.progress(0.0, text="Searching Spotify...")
    matches = []
    for i, query in enumerate(queries, 1):
        matches.append((query, find_best_match(client, query).track))
        progress.progress(i / len(queries), text=f"Searching Spotify... {i}/{len(queries)}")
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
    use_container_width=True,
    hide_index=True,
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
