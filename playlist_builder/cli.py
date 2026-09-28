"""CLI entrypoint: reads a song list from a source, matches it against
Spotify, and creates a playlist from whatever was found."""
import argparse

from playlist_builder.config import ConfigError
from playlist_builder.matcher import find_best_match
from playlist_builder.parser import parse_lines
from playlist_builder.sources import image_source, text_source, website_source
from playlist_builder.spotify_client import SpotifyClient


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a Spotify playlist from a website, pasted text, or an image of a playlist."
    )
    parser.add_argument("--source", required=True, choices=["text", "website", "image"])
    parser.add_argument("--text-file", help="Path to a text file (or '-' for stdin) for --source text.")
    parser.add_argument("--url", help="Page URL to scrape for --source website.")
    parser.add_argument("--image", help="Path to an image file for --source image.")
    parser.add_argument("--playlist-name", required=True, help="Name for the created Spotify playlist.")
    parser.add_argument("--description", default="", help="Optional playlist description.")
    parser.add_argument("--public", action="store_true", help="Make the playlist public (default: private).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search and match only; don't create or modify anything on Spotify.",
    )
    return parser


def _get_raw_text(args: argparse.Namespace) -> str:
    if args.source == "text":
        return text_source.read_text(args.text_file)
    if args.source == "website":
        if not args.url:
            raise SystemExit("--url is required when --source website")
        return website_source.fetch_song_lines(args.url)
    if args.source == "image":
        if not args.image:
            raise SystemExit("--image is required when --source image")
        return image_source.extract_text(args.image)
    raise SystemExit(f"Unknown source: {args.source}")


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)

    raw_text = _get_raw_text(args)
    queries = parse_lines(raw_text)
    if not queries:
        print("No song entries found in the input.")
        return

    try:
        client = SpotifyClient()
    except ConfigError as e:
        raise SystemExit(str(e))

    found_uris = []
    skipped = []
    for query in queries:
        result = find_best_match(client, query)
        if result.track:
            artists = ", ".join(a["name"] for a in result.track["artists"])
            print(f"[OK]   {query.raw_line}  ->  {result.track['name']} - {artists}")
            found_uris.append(result.track["uri"])
        else:
            print(f"[skip] {query.raw_line}")
            skipped.append(query.raw_line)

    print(f"\n{len(found_uris)} found, {len(skipped)} skipped out of {len(queries)} total.")

    if args.dry_run:
        print("Dry run: not creating a playlist.")
        return

    if not found_uris:
        print("No tracks matched; not creating an empty playlist.")
        return

    playlist = client.create_playlist(args.playlist_name, public=args.public, description=args.description)
    client.add_tracks(playlist["id"], found_uris)
    print(f"\nCreated playlist: {playlist['external_urls']['spotify']}")


if __name__ == "__main__":
    main()
