"""Deterministic, bounded views of recorded bytes. No extraction or execution."""

import base64
import gzip
import io
import stat
import struct
import tarfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath

__all__ = ["PreviewError", "preview_byte_limit", "preview_file"]


class PreviewError(ValueError):
    """The requested preview is unavailable. `code` is machine-readable."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code

MAX_INLINE_BYTES = 512 * 1024
MAX_CONTAINER_BYTES = 16 * 1024 * 1024
_MAX_DECODED = 64 * 1024 * 1024
_MAX_TEXT = 16_000
_MAX_MEMBERS = 32
_TEXT = frozenset({
    ".csv", ".ini", ".ipynb", ".json", ".jsonl", ".md", ".py", ".r", ".sh",
    ".tex", ".toml", ".tsv", ".txt", ".yaml", ".yml",
})
_IMAGES = {".png": "image/png", ".jpeg": "image/jpeg", ".jpg": "image/jpeg"}
_CONTAINERS = {".tar", ".tgz", ".gz", ".zip"}


def _has(path, suffixes):
    return Path(path).suffix.lower() in suffixes


def preview_byte_limit(name: str) -> int:
    """Maximum stored bytes the preview API accepts for this filename."""
    return MAX_CONTAINER_BYTES if _has(name, _CONTAINERS) else MAX_INLINE_BYTES


def _read(stream, size, *, offset=0):
    if offset + size > _MAX_DECODED:
        raise PreviewError("This preview exceeds the decoded size limit.", "too_large")
    stream.seek(offset)
    return stream.read(size)


def _idx(stream, start):
    magic, count = struct.unpack(">II", _read(stream, 8))
    if magic == 2051:
        rows, columns = struct.unpack(">II", _read(stream, 8, offset=8))
        if not 1 <= rows <= 128 or not 1 <= columns <= 128:
            raise PreviewError("The recorded image dimensions exceed inline preview limits.", "cannot_decode")
        width, header, page_size = rows * columns, 16, 8
    else:
        rows, columns, width, header, page_size = None, None, 1, 8, 32
    if not count:
        return {"kind": "metadata", "description": "The IDX file has no records."}
    if start >= count:
        raise PreviewError("The starting record is outside the dataset.", "outside_window")
    end = min(start + page_size, count)
    records = _read(stream, (end - start) * width, offset=header + start * width)
    if len(records) != (end - start) * width:
        raise PreviewError("The IDX window is incomplete.", "cannot_decode")
    return {
        "kind": "idx", "start": start, "end": end, "total": count,
        "page_size": page_size, "rows": rows, "columns": columns,
        "records": base64.b64encode(records).decode("ascii"),
    }


def _regular(name, content):
    suffix = Path(name).suffix.lower()
    if suffix in _IMAGES:
        return {
            "kind": "image", "media_type": _IMAGES[suffix],
            "data": base64.b64encode(content).decode("ascii"),
        }
    if suffix in _TEXT:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise PreviewError("This evidence file is not UTF-8 text.", "cannot_decode") from None
        return {"kind": "text", "text": text[:_MAX_TEXT], "truncated": len(text) > _MAX_TEXT}
    return {"kind": "metadata", "description": "Inline preview is unavailable for this format."}


class _BoundedArchive:
    def __init__(self, stream):
        self.stream = stream

    def tell(self):
        return self.stream.tell()

    def seek(self, offset):
        if not 0 <= offset <= _MAX_DECODED:
            raise PreviewError("The archive preview exceeds its scan limit.", "too_large")
        return self.stream.seek(offset)

    def read(self, size):
        if not 0 <= size <= _MAX_DECODED - self.tell():
            raise PreviewError("The archive preview exceeds its scan limit.", "too_large")
        return self.stream.read(size)


def _safe_member(name):
    path = PurePosixPath(name)
    return bool(path.parts) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _zip(stream, selected, start):
    # Read the end record before zipfile allocates its central directory.
    size = stream.seek(0, io.SEEK_END)
    stream.seek(max(0, size - 65_557))
    tail = stream.read()
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0:
        raise PreviewError("Archive directory is unavailable.", "cannot_decode")
    end = struct.unpack_from("<4s4H2LH", tail, offset)
    if (
        end[1] or end[2] or end[3] != end[4] or end[4] > 4096
        or end[5] > MAX_INLINE_BYTES
        or tail[max(0, offset - 20):offset - 16] == b"PK\x06\x07"
        or offset + 22 + end[-1] != len(tail)
    ):
        raise PreviewError("The archive directory exceeds its preview limits.", "too_large")
    members = []
    with zipfile.ZipFile(stream) as archive:
        for index, item in enumerate(archive.infolist()[:_MAX_MEMBERS]):
            if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16) or not _safe_member(item.filename):
                continue
            members.append({"id": index, "name": item.filename, "size": item.file_size})
            if selected == index:
                if item.file_size > MAX_INLINE_BYTES:
                    raise PreviewError("This archive member exceeds the inline size limit.", "too_large")
                with archive.open(item) as resource:
                    data = resource.read(MAX_INLINE_BYTES + 1)
                if len(data) > MAX_INLINE_BYTES:
                    raise PreviewError("This archive member exceeds the inline size limit.", "too_large")
                return {
                    "member": item.filename,
                    **_decode(item.filename, io.BytesIO(data), start, None, nested=True),
                }
    if selected is not None:
        raise PreviewError("This archive member is outside the preview listing.", "member_not_found")
    return {"kind": "archive", "members": members}


def _tar(stream, selected, start):
    members = []
    with tarfile.open(fileobj=_BoundedArchive(stream), mode="r:") as archive:
        for index, member in enumerate(archive):
            if index >= _MAX_MEMBERS or member.offset_data > _MAX_DECODED:
                break
            if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE} or not _safe_member(member.name):
                continue
            if member.offset_data + member.size > _MAX_DECODED:
                break
            members.append({"id": index, "name": member.name, "size": member.size})
            if selected == index:
                if member.size > MAX_INLINE_BYTES:
                    raise PreviewError("This archive member exceeds the inline size limit.", "too_large")
                with archive.extractfile(member) as resource:
                    return {
                        "member": member.name,
                        **_decode(member.name, io.BytesIO(resource.read()), start, None, nested=True),
                    }
    if selected is not None:
        raise PreviewError("This archive member is outside the preview listing.", "member_not_found")
    return {"kind": "archive", "members": members}


def _decode(name, stream, start, member, *, nested=False):
    header = _read(stream, 4)
    if header in (b"\x00\x00\x08\x01", b"\x00\x00\x08\x03"):
        return _idx(stream, start)
    lower = name.lower()
    if not nested and lower.endswith(".zip"):
        return _zip(stream, member, start)
    if not nested and lower.endswith((".tar", ".tar.gz", ".tgz")):
        stream.seek(0)
        return _tar(stream, member, start)
    if _has(name, _TEXT | _IMAGES.keys()):
        data = _read(stream, MAX_INLINE_BYTES + 1)
        if len(data) > MAX_INLINE_BYTES:
            raise PreviewError("The decoded file exceeds the inline size limit.", "too_large")
        return _regular(name, data)
    return _regular(name, b"")


def preview_file(
    name: str, content: bytes, *, start: int = 0, member: int | None = None,
) -> dict:
    """Decode a bounded window from supplied bytes and return JSON-safe data.

    ``start`` is a zero-based record offset and ``member`` selects an ID from
    an archive listing. Callers supply the original filename and are responsible
    for access and provenance checks before providing its contents.
    """
    if type(start) is not int or start < 0 or (
        member is not None and (type(member) is not int or member < 0)
    ):
        raise PreviewError("Invalid preview window or member.", "invalid_selector")
    if len(content) > preview_byte_limit(name):
        raise PreviewError("The stored file exceeds its preview limit.", "too_large")
    try:
        with io.BytesIO(content) as stream:
            if content.startswith(b"\x1f\x8b"):
                with gzip.GzipFile(fileobj=stream) as decoded:
                    decoded_name = name if name.lower().endswith((".tar.gz", ".tgz")) else name[:-3]
                    return _decode(decoded_name, decoded, start, member)
            return _decode(name, stream, start, member)
    except (OSError, EOFError, RuntimeError, struct.error, tarfile.TarError, zipfile.BadZipFile, zlib.error):
        raise PreviewError("The recorded file could not be decoded for preview.", "cannot_decode") from None
