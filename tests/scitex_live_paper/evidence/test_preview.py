import io
import tarfile
import zipfile

import pytest

from scitex_live_paper.evidence.preview import PreviewError, preview_byte_limit, preview_file


@pytest.mark.parametrize("name", ["original.zip", "original.tar.gz"])
def test_archive_lists_and_reads_only_safe_members(name):
    data = io.BytesIO()
    if name.endswith(".zip"):
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("../outside.txt", "outside")
            archive.writestr("folder/report.txt", "inside")
    else:
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            for filename, content in [("../outside.txt", b"outside"), ("folder/report.txt", b"inside")]:
                item = tarfile.TarInfo(filename)
                item.size = len(content)
                archive.addfile(item, io.BytesIO(content))
    payload = data.getvalue()

    listing = preview_file(name, payload)
    member = preview_file(name, payload, member=1)
    with pytest.raises(PreviewError) as error:
        preview_file(name, payload, member=0)

    assert (
        listing["members"], member["text"], error.value.code,
    ) == ([{"id": 1, "name": "folder/report.txt", "size": 6}], "inside", "member_not_found")


def test_idx_vector_exposes_numbers_without_inferred_labels():
    import base64
    import gzip
    import struct

    data = gzip.compress(struct.pack(">II", 2049, 3) + b"\x05\x00\x04")
    view = preview_file("bytes.gz", data)

    assert (
        view["kind"], view["rows"], view["columns"], base64.b64decode(view["records"]),
    ) == ("idx", None, None, b"\x05\x00\x04")



def test_library_enforces_limits_without_an_http_caller():
    with pytest.raises(PreviewError) as oversized:
        preview_file("source.bin", bytes(preview_byte_limit("source.bin") + 1))
    with pytest.raises(PreviewError) as invalid:
        preview_file("source.bin", b"", start=-1)

    assert (oversized.value.code, invalid.value.code) == ("too_large", "invalid_selector")
