"""Reads raw playlist text from a file or stdin."""
import sys


def read_text(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
