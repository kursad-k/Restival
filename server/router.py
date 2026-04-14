"""server/router.py — URL pattern router.

RegexRouter maps compiled regex patterns to handler callables.
Path parameters are extracted as named groups and URL-decoded before returning.
First-registered pattern wins on ambiguous matches.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import unquote


class RegexRouter:
    """Register URL patterns and resolve incoming paths to (handler, params)."""

    def __init__(self) -> None:
        self._routes: list[tuple[re.Pattern[str], Callable[..., Any]]] = []

    def register(self, pattern: str, handler: Callable[..., Any]) -> None:
        """Add a route. First registered wins on ambiguous overlaps."""
        self._routes.append((re.compile(pattern), handler))

    def resolve(
        self, path: str
    ) -> tuple[Callable[..., Any], dict[str, str]] | None:
        """Match *path* against registered patterns.

        Returns (handler, params) on match, None on no match.
        Named capture groups become path params; values are URL-decoded.
        """
        for pattern, handler in self._routes:
            m = pattern.match(path)
            if m:
                params = {k: unquote(v) for k, v in m.groupdict().items()}
                return handler, params
        return None
