"""Loads Spotify API credentials from a .env file or the environment."""
import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")


class ConfigError(RuntimeError):
    pass


def get_spotify_credentials() -> dict:
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your Spotify app credentials."
        )
    return {name: os.environ[name] for name in REQUIRED_VARS}
