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
        self._routes: list[tuple[re.Pattern[str], str, Callable[..., Any]]] = []

    def register(self, pattern: str, handler: Callable[..., Any], method: str = "GET") -> None:
        """Add a route. First registered wins on ambiguous overlaps."""
        self._routes.append((re.compile(pattern), method.upper(), handler))

    def resolve(
        self, path: str, method: str = "GET"
    ) -> tuple[Callable[..., Any], dict[str, str]] | None:
        """Match *path* and *method* against registered patterns.

        Returns (handler, params) on match, None on no match.
        Named capture groups become path params; values are URL-decoded.
        """
        method = method.upper()
        for pattern, route_method, handler in self._routes:
            if route_method != method:
                continue
            m = pattern.match(path)
            if m:
                params = {k: unquote(v) for k, v in m.groupdict().items()}
                return handler, params
        return None
