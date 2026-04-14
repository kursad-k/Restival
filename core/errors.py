"""core/errors.py — domain error types used across api/ and server/ layers."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist in the Blender scene."""


class BadRequestError(Exception):
    """Raised when query parameters fail validation (e.g. page_size > 200)."""
