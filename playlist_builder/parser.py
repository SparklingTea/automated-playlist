"""Turns raw text lines (from any source) into normalized song queries."""
import re
from dataclasses import dataclass

_LEADING_MARKER_RE = re.compile(r"^\s*(?:[-*•‣▪]|\(?\d+[.)])\s*")
_QUOTE_CHARS = "\"'“”‘’"
_DASH_SPLIT_RE = re.compile(r"\s+[-–—]\s+")
_BY_SPLIT_RE = re.compile(r"^(.+?)\s+by\s+(.+)$", re.IGNORECASE)


@dataclass
class SongQuery:
    raw_line: str
    title: str | None = None
    artist: str | None = None
    # Set when the raw line's ordering is ambiguous (e.g. "A - B"), so the
    # matcher can try the reverse interpretation if the first doesn't match.
    alt_title: str | None = None
    alt_artist: str | None = None

    def query_variants(self) -> list[tuple[str | None, str | None]]:
        """Returns (title, artist) pairs to try, in priority order."""
        variants = [(self.title, self.artist)]
        if self.alt_title is not None or self.alt_artist is not None:
            variants.append((self.alt_title, self.alt_artist))
        return variants


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] in _QUOTE_CHARS and text[-1] in _QUOTE_CHARS:
        text = text[1:-1].strip()
    return text


def _strip_line(line: str) -> str:
    return _unquote(_LEADING_MARKER_RE.sub("", line))


def _parse_line(cleaned: str) -> SongQuery:
    by_match = _BY_SPLIT_RE.match(cleaned)
    dash_parts = _DASH_SPLIT_RE.split(cleaned, maxsplit=1)

    if len(dash_parts) == 2:
        a, b = _unquote(dash_parts[0]), _unquote(dash_parts[1])
        return SongQuery(
            raw_line=cleaned,
            title=a,
            artist=b,
            alt_title=b,
            alt_artist=a,
        )

    if by_match:
        title, artist = _unquote(by_match.group(1)), _unquote(by_match.group(2))
        return SongQuery(raw_line=cleaned, title=title, artist=artist)

    return SongQuery(raw_line=cleaned, title=cleaned, artist=None)


def parse_lines(raw_text: str) -> list[SongQuery]:
    """Parses raw multi-line text into deduplicated SongQuery objects."""
    seen: set[str] = set()
    queries: list[SongQuery] = []
    for line in raw_text.splitlines():
        cleaned = _strip_line(line)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(_parse_line(cleaned))
    return queries
