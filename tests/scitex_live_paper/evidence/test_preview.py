import base64
import gzip
import io
import struct
import tarfile
import zipfile

import pytest

from scitex_live_paper.evidence.preview import PreviewError, preview_byte_limit, preview_file


@pytest.fixture(params=["original.zip", "original.tar.gz"])
def original_archive(request):
    name = request.param
    files = [("../outside.txt", b"outside"), ("folder/report.txt", b"inside")]
    data = io.BytesIO()
    if name.endswith(".zip"):
        with zipfile.ZipFile(data, "w") as archive:
            for filename, content in files:
                archive.writestr(filename, content)
    else:
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            for filename, content in files:
                item = tarfile.TarInfo(filename)
                item.size = len(content)
                archive.addfile(item, io.BytesIO(content))
    return name, data.getvalue()


def test_archive_lists_and_reads_safe_members(original_archive):
    # Arrange
    name, payload = original_archive
    # Act
    listing = preview_file(name, payload)
    member = preview_file(name, payload, member=1)
    # Assert
    assert (listing["members"], member["text"]) == (
        [{"id": 1, "name": "folder/report.txt", "size": 6}], "inside",
    )


def test_archive_refuses_member_outside_the_listing(original_archive):
    # Arrange
    name, payload = original_archive
    # Act
    preview = lambda: preview_file(name, payload, member=0)
    # Assert
    with pytest.raises(PreviewError, match="outside the preview listing"):
        preview()


def test_idx_vector_exposes_numbers_without_inferred_labels():
    # Arrange
    data = gzip.compress(struct.pack(">II", 2049, 3) + b"\x05\x00\x04")
    # Act
    view = preview_file("bytes.gz", data)
    # Assert
    assert (
        view["kind"], view["rows"], view["columns"], base64.b64decode(view["records"]),
    ) == ("idx", None, None, b"\x05\x00\x04")


def test_library_enforces_limits_without_an_http_caller():
    # Arrange
    data = bytes(preview_byte_limit("source.bin") + 1)
    # Act
    preview = lambda: preview_file("source.bin", data)
    # Assert
    with pytest.raises(PreviewError, match="stored file exceeds"):
        preview()


def test_library_rejects_negative_windows():
    # Arrange
    name, data = "source.bin", b""
    # Act
    preview = lambda: preview_file(name, data, start=-1)
    # Assert
    with pytest.raises(PreviewError, match="Invalid preview window or member"):
        preview()
