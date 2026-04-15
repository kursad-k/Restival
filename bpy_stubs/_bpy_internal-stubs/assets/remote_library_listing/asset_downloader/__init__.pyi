import typing
import collections.abc
import typing_extensions
import numpy.typing as npt

class AssetDownloader:
    OnAssetDoneCallback: typing.Any
    OnDoneCallback: typing.Any
    OnUpdateCallback: typing.Any
    error_message: typing.Any
    local_path: typing.Any
    remote_url: typing.Any
    status: typing.Any

    def already_downloaded(self, http_req_descr, local_file) -> None:
        """

        :param http_req_descr:
        :param local_file:
        """

    def download_asset_file(self, asset_url, save_to) -> None:
        """Download an asset or preview file to a local file.

        :param asset_url:
        :param save_to:
        """

    def download_error(self, http_req_descr, local_file, error) -> None:
        """

        :param http_req_descr:
        :param local_file:
        :param error:
        """

    def download_finished(self, http_req_descr, local_file) -> None:
        """

        :param http_req_descr:
        :param local_file:
        """

    def download_progress(
        self, http_req_descr, content_length_bytes, downloaded_bytes
    ) -> None:
        """

        :param http_req_descr:
        :param content_length_bytes:
        :param downloaded_bytes:
        """

    def download_starts(self, http_req_descr) -> None:
        """

        :param http_req_descr:
        """

    def on_timer_event(self) -> None: ...
    def report(self, level, message) -> None:
        """

        :param level:
        :param message:
        """

    def shutdown(self, status) -> None:
        """Stop the background downloader, update the status and call the done callback.

        :param status:
        """

    def start(self) -> None:
        """Start the background process."""

class DownloadStatus:
    """Create a collection of name/value pairs.Example enumeration:Access them by:Enumerations can be iterated over, and know how many members they have:Methods can be added to enumerations, and members can have their own
    attributes -- see the documentation for details.
    """

    DOWNLOADING: typing.Any
    FAILED: typing.Any
    FINISHED: typing.Any
    IDLE: typing.Any
    name: typing.Any
    value: typing.Any

def download_asset_file(
    asset_library_url, asset_library_local_path, asset_url, asset_hash, save_to
) -> None:
    """Download an asset file to a file on disk.

        :param asset_library_url: Root URL of the remote asset library. Used as an
    identifier of this library (to create a downloader per library), as well
    as for resolving relative URLs.
        :param asset_library_local_path: Root path of the local asset cache. Used to
    resolve relative save_to paths, but also to find the HTTP metadata
    cache for this asset library (for conditional downloads).
        :param asset_url: the URL to download. Can be absolute or relative to the
    asset library URL. If it is an empty string, the save_to path is used
    as the URL.
        :param asset_hash: the hash of the asset file, will be appended to the URL.
        :param save_to: the path on disk where to download to. While the download is
    pending, ".part" will be appended to the filename. When the download
    finishes successfully, it is renamed to the final path.
    """

def download_preview(
    asset_library_url, asset_library_local_path, preview_url, preview_hash, dst_filepath
) -> None:
    """Download an asset preview to a file on disk.

        :param asset_library_url: Root URL of the remote asset library. Used as an
    identifier of this library (to create a downloader per library), as well
    as for resolving relative URLs.
        :param asset_library_local_path: Root path of the local asset cache. Used to
    resolve relative save_to paths, but also to find the HTTP metadata
    cache for this asset library (for conditional downloads).
        :param preview_url: the URL to download. Can be absolute or relative.
        :param preview_hash: the hash of the thumbnail, will be appended to the URL.
        :param dst_filepath: the path on disk where to download to. While the
    download is pending, ".part" will be appended to the filename. When the
    download finishes successfully, it is renamed to the final path.
    """

def downloader_status(asset_library_url) -> None:
    """Returns the asset downloader status.Raises a KeyError if there never was a downloader for this URL."""
