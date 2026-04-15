import typing
import collections.abc
import typing_extensions
import numpy.typing as npt

class AssetLibraryIndexPageV1:
    """AssetLibraryIndexPageV1(asset_count: int, file_count: int, assets: list[AssetV1], files: list[FileV1])"""

class AssetLibraryIndexV1:
    """AssetLibraryIndexV1(schema_version: str, asset_size_bytes: int, asset_count: int, file_count: int, pages: list[URLWithHash], catalogs: list[CatalogV1] | None = None)"""

    catalogs: typing.Any

class AssetLibraryMeta:
    """AssetLibraryMeta(api_versions: dict[str, URLWithHash], name: str, contact: Contact)"""

class AssetMetadataV1:
    """AssetMetadataV1(catalog_id: str | None = None, tags: list[str] | None = None, author: str | None = None, description: str | None = None, license: str | None = None, copyright: str | None = None, properties: CustomPropertiesV1 | None = None)"""

    author: typing.Any
    catalog_id: typing.Any
    copyright: typing.Any
    description: typing.Any
    license: typing.Any
    properties: typing.Any
    tags: typing.Any

class AssetV1:
    """AssetV1(name: str, id_type: AssetIDTypeV1, files: list[str], thumbnail: URLWithHash | None = None, meta: AssetMetadataV1 | None = None)"""

    meta: typing.Any
    thumbnail: typing.Any

class CatalogV1:
    """CatalogV1(path: str, uuids: list[str], simple_name: str | None = None)"""

    simple_name: typing.Any

class Contact:
    """Contact(name: str, url: str | None = None, email: str | None = None)"""

    email: typing.Any
    url: typing.Any

class CustomPropertyTypeV1:
    """Enum where members are also (and must be) strings"""

    IDP_ARRAY: typing.Any
    IDP_BOOLEAN: typing.Any
    IDP_DOUBLE: typing.Any
    IDP_FLOAT: typing.Any
    IDP_GROUP: typing.Any
    IDP_INT: typing.Any
    IDP_STRING: typing.Any

class CustomPropertyV1:
    """CustomPropertyV1(name: str, type: CustomPropertyTypeV1, value: CustomPropertiesV1 | list[Any] | float | int | str | bool, itemtype: CustomPropertyTypeV1 | None = None)"""

    itemtype: typing.Any

class FileV1:
    """FileV1(path: str, size_in_bytes: int, hash: str, blender_version: str, url: str | None = None)"""

    url: typing.Any

class URLWithHash:
    """URLWithHash(url: str, hash: str)"""
