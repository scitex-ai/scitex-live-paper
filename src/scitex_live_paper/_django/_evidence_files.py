"""Descriptor-rooted reads for an authorized manuscript resource directory."""

from __future__ import annotations

import errno
import os
import stat
from contextlib import contextmanager
from pathlib import Path

DEFAULT_MAX_REPORT_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_TEXT_BYTES = 4 * 1024 * 1024


class ResourceError(Exception):
    def __init__(self, message: str, status: int):
        self.status = status
        super().__init__(message)


def _filesystem_error(error: OSError) -> ResourceError:
    if error.errno == errno.ENOENT:
        return ResourceError("Paper resource not found", 404)
    if error.errno in {errno.ELOOP, errno.ENOTDIR, errno.EACCES, errno.EPERM}:
        return ResourceError("Paper resource is not accessible", 403)
    return ResourceError("Paper resource storage is unavailable", 503)


class ResourceReader:
    """Open regular files without following replaceable path components.

    The host supplies this root. A report's project_root never selects it.
    Each request owns its descriptors; no cwd or environment is changed.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self._fd = None

    def __enter__(self):
        if not self.root.is_absolute() or ".." in self.root.parts:
            raise ResourceError("An absolute paper resource root is required", 503)
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise ResourceError("Secure paper resource reads are unavailable", 503)
        flags = getattr(os, "O_PATH", os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
        cursor = None
        try:
            cursor = os.open(self.root.anchor, flags)
            for component in self.root.parts[1:]:
                child = os.open(component, flags, dir_fd=cursor)
                os.close(cursor)
                cursor = child
            self._fd = cursor
        except OSError as error:
            if cursor is not None:
                os.close(cursor)
            raise _filesystem_error(error) from None
        return self

    def __exit__(self, *_args):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _open(self, name: str | Path):
        path = Path(name)
        if path.is_absolute():
            try:
                path = path.relative_to(self.root)
            except ValueError:
                raise ResourceError("Paper resources must stay inside the authorized root", 403) from None
        if not path.parts or any(part == ".." for part in path.parts):
            raise ResourceError("Paper resource path is invalid", 403)
        if self._fd is None:
            raise ResourceError("Paper resource reader is not open", 503)
        flags = getattr(os, "O_PATH", os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
        cursor = os.dup(self._fd)
        try:
            for component in path.parts[:-1]:
                child = os.open(component, flags, dir_fd=cursor)
                os.close(cursor)
                cursor = child
            return os.open(
                path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=cursor,
            )
        except OSError as error:
            raise _filesystem_error(error) from None
        except ValueError:
            raise ResourceError("Paper resource path is invalid", 400) from None
        finally:
            os.close(cursor)

    @contextmanager
    def open_regular_file(self, name: str | Path):
        """Open a regular file beneath the root for a bounded caller operation."""
        try:
            with os.fdopen(self._open(name), "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ResourceError("Paper resource must be a regular file", 403)
                yield stream
        except OSError as error:
            raise _filesystem_error(error) from None

    def check_regular_file(self, name: str) -> None:
        """Check that a source can be opened beneath the root without reading it."""
        with self.open_regular_file(name):
            pass

    def read(self, name: str, *, limit: int) -> bytes:
        if type(limit) is not int or limit <= 0:
            raise ResourceError("Paper resource limits are not configured correctly", 503)
        try:
            with os.fdopen(self._open(name), "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ResourceError("Paper resource must be a regular file", 403)
                if info.st_size > limit:
                    raise ResourceError("Paper resource exceeds its size limit", 413)
                content = stream.read(limit + 1)
                if len(content) > limit:
                    raise ResourceError("Paper resource exceeds its size limit", 413)
                return content
        except OSError as error:
            raise _filesystem_error(error) from None
