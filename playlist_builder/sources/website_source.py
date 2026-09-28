"""Best-effort scraper that pulls candidate song lines out of a web page.

Works well for pages that list songs as <li>/table rows or as plain
"Artist - Title" text. Doesn't render JavaScript, so pages that build their
track list client-side won't produce useful output.
"""
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; PlaylistBuilder/1.0)"
TRACK_CLASS_HINTS = ("track", "song", "title")
MIN_STRUCTURED_CANDIDATES = 3


def fetch_song_lines(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    structured = _extract_structured(soup)
    lines = structured if len(structured) >= MIN_STRUCTURED_CANDIDATES else _extract_from_text(soup)
    return "\n".join(lines)


def _extract_structured(soup: BeautifulSoup) -> list[str]:
    candidates = []
    for tag in soup.find_all(["li", "tr"]):
        text = tag.get_text(" ", strip=True)
        if text:
            candidates.append(text)
    for tag in soup.find_all(class_=True):
        classes = " ".join(tag.get("class", [])).lower()
        if any(hint in classes for hint in TRACK_CLASS_HINTS):
            text = tag.get_text(" ", strip=True)
            if text:
                candidates.append(text)
    return _dedupe(candidates)


def _extract_from_text(soup: BeautifulSoup) -> list[str]:
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    return _dedupe(line for line in lines if line)


def _dedupe(lines) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in lines:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            result.append(line)
    return result
