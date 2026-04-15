"""
This module provides access to image buffer types.

[NOTE]
Image buffer is also the structure used by bpy.types.Image
ID type to store and manipulate image data at runtime.

"""

import typing
import collections.abc
import typing_extensions
import numpy.typing as npt

class ImBuf:
    channels: int
    """ Number of color channels."""

    compress: int
    """ Compression level for formats that support lossless compression levels (0 - 100, clamped)."""

    file_type: str
    """ The file type identifier."""

    filepath: bytes | str
    """ Filepath associated with this image."""

    planes: int
    """ Number of bits per pixel for the byte buffer.
Used when reading and writing image files."""

    ppm: tuple[float, float]
    """ Pixels per meter."""

    quality: int
    """ Quality for formats that support lossy compression (0 - 100, clamped)."""

    size: tuple[int, int]
    """ Size of the image in pixels."""

    def clear_buffer(self, type: typing.Literal["BYTE", "FLOAT"]) -> None:
        """Free pixel data of the given type.

        :param type: The buffer type.
        """

    def copy(self) -> typing_extensions.Self:
        """Return a copy of the image.

        :return: A copy of the image.
        """

    def crop(self, min: tuple[int, int], max: tuple[int, int]) -> None:
        """Crop the image in-place.

        :param min: Minimum pixel coordinates (X, Y), inclusive.
        :param max: Maximum pixel coordinates (X, Y), inclusive.
        """

    def ensure_buffer(self, type: typing.Literal["BYTE", "FLOAT"]) -> None:
        """Ensure the image has pixel data of the given type.
        If absent, it is allocated and converted from the other buffer when available.

                :param type: The buffer type.
        """

    def free(self) -> None:
        """Clear image data immediately (causing an error on re-use)."""

    def has_buffer(self, type: typing.Literal["BYTE", "FLOAT"]) -> bool:
        """Return whether the image has pixel data of the given type.

        :param type: The buffer type.
        :return: True if the buffer exists.
        """

    def resize(self, size: tuple[int, int], *, method: str = "FAST") -> None:
        """Resize the image in-place.

        :param size: New size.
        :param method: Method of resizing (FAST, BILINEAR).
        """

    def with_buffer(
        self,
        type: typing.Literal["BYTE", "FLOAT"],
        *,
        write: bool = False,
        region: None | tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> ImBufBuffer:
        """Return a context manager that yields a `memoryview` of the images pixel data.Usage:

                :param type: The buffer type.
                :param write: When true the buffer is writable.
                :param region: Optional sub-region ((x_min, y_min), (x_max, y_max)).
        When set the memoryview is 2D (rows x columns), clamped to image bounds.
                :return: A context manager yielding a `memoryview` of pixel data.
        """

class ImBufBuffer: ...

class ImBufFileType:
    file_extensions: typing.Any
    """ Undocumented, consider contributing."""

    has_read_file: typing.Any
    """ Undocumented, consider contributing."""

    has_read_memory: typing.Any
    """ Undocumented, consider contributing."""

    has_write_file: typing.Any
    """ Undocumented, consider contributing."""

    has_write_memory: typing.Any
    """ Undocumented, consider contributing."""

    id: typing.Any
    """ Undocumented, consider contributing."""
