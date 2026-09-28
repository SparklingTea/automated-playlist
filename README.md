# Playlist Builder

Turns a playlist described as a website, pasted text, or a screenshot/photo of a
playlist into a real Spotify playlist. Each entry is looked up on Spotify and
skipped if no confident match is found.

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Create a Spotify Developer app

1. Go to https://developer.spotify.com/dashboard and log in.
2. Click **Create app**.
3. Fill in a name/description. For **Redirect URI**, use `http://localhost:8888/callback`.
4. Save, then open the app's settings to find your **Client ID** and **Client Secret**.

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in the values from step 2:

```
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

The first time you run the tool, a browser window will open asking you to log
in to Spotify and approve access. After that, the auth token is cached in
`.spotify_cache` in this folder.

### 4. Install Tesseract OCR (only needed for `--source image`)

`pytesseract` needs the Tesseract binary installed separately:

- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki, then
  either add it to your `PATH` or set `TESSERACT_CMD` in `.env` to the full
  path of `tesseract.exe` (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

## Usage

### Web app (Streamlit)

```
streamlit run app.py
```

Paste a playlist page URL or upload a screenshot, review/edit the extracted
song list, match it on Spotify, then create the playlist.

### CLI

```
python main.py --source text --text-file songs.txt --playlist-name "My Playlist"
python main.py --source text --text-file - --playlist-name "My Playlist"   # paste via stdin
python main.py --source website --url "https://example.com/some-playlist-page" --playlist-name "Scraped"
python main.py --source image --image screenshot.png --playlist-name "From a Photo"
```

Add `--dry-run` to see what would be matched without creating anything on
Spotify. Add `--public` to make the created playlist public (default:
private). Add `--description "..."` to set a playlist description.

Supported text line formats: `Artist - Title`, `Title - Artist` (both
orderings are tried), `Title by Artist`, and plain titles. Leading numbering,
bullets, and quote marks are stripped automatically.

## Limitations

- **Website scraping** is best-effort and generic: it looks for `<li>`/table
  rows or elements with a track/song/title-like class, falling back to raw
  visible text. It does not render JavaScript, so pages that build their
  track list client-side (most modern SPA-style sites) won't produce useful
  results.
- **Matching** uses fuzzy string similarity against Spotify search results
  and requires an ~70% similarity score to accept a match; ambiguous or
  obscure titles may be skipped even if the track exists.

## Tests

```
pytest
```

Covers the text parser and the matching/scoring logic. The Spotify OAuth,
search, and playlist-creation flow requires real credentials and a
browser-based login, so it isn't covered by automated tests — run the CLI
directly (ideally with `--dry-run` first) to verify it end-to-end.
