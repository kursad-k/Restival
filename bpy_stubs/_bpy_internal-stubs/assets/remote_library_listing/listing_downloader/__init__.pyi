import typing
import collections.abc
import typing_extensions
import numpy.typing as npt

class DownloadStatus:
    """Create a collection of name/value pairs.Example enumeration:Access them by:Enumerations can be iterated over, and know how many members they have:Methods can be added to enumerations, and members can have their own
    attributes -- see the documentation for details.
    """

    FAILED: typing.Any
    FINISHED_SUCCESSFULLY: typing.Any
    LOADING: typing.Any
    name: typing.Any
    value: typing.Any

class RemoteAssetListingDownloader:
    """Download a remote asset listing.Calling downloader.download_and_process() performs the following steps:The above steps always happen, even when the HTTP server returns a 304 Not
    Modified.
    """

    OnDoneCallback: typing.Any
    OnMetafilesDoneCallback: typing.Any
    OnPageDoneCallback: typing.Any
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

    def download_and_process(self) -> None:
        """Download and process the remote library index."""

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

    def on_asset_page_downloaded(self, http_req_descr, unsafe_local_file) -> None:
        """

        :param http_req_descr:
        :param unsafe_local_file:
        """

    def on_timer_event(self) -> None: ...
    def parse_asset_lib_index(self, http_req_descr, unsafe_local_file) -> None:
        """

        :param http_req_descr:
        :param unsafe_local_file:
        """

    def parse_asset_lib_metadata(self, http_req_descr, unsafe_local_file) -> None:
        """

        :param http_req_descr:
        :param unsafe_local_file:
        """

    def report(self, level, message) -> None:
        """

        :param level:
        :param message:
        """

    def shutdown(self, status) -> None:
        """Stop the background downloader, update the status and call the done callback.

        :param status:
        """

class RemoteAssetListingLocator:
    """Construct paths for various components of a remote asset library.Basically this determines where assets are downloaded, what their filenames
    will be, and where the HTTP metadata cache is located.
    """

    catalogs_file: typing.Any
    http_metadata_cache_location: typing.Any
    local_path: typing.Any
    remote_url: typing.Any

    def asset_download_path(self, asset_file) -> None:
        """Construct the absolute download path for this asset.This can raise a ValueError if the file path is not suitable (either
        downright invalid, or not ending in .blend).

                :param asset_file:
        """

def is_more_recent_than(library_path, max_age_sec) -> None:
    """Return whether the remote asset library listing is more recent than the given age.If the listing hasnt been downloaded, return False."""
