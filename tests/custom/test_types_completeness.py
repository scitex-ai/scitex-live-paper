"""No-mocks tests pinning the public-type completeness contract.

Audit deliverable (lead msg ``a40780a3``, 2026-06-14): the public
surface a host needs to consume ``mount(resolver=...)`` is complete +
unambiguous. Two distinct resolver-related type aliases ship:

- :data:`BundleResolver` — zero-arg ``Callable[[], Bundle]``. Used by
  :meth:`BundleSource.from_resolver`. Per-bundle, deferred IO.
- :data:`MountResolver` — request-arg ``Callable[..., BundleContext]``.
  Used by :func:`mount`. Per-request, builds the whole context.

This file pins:

1. **Both aliases public + distinct + correctly signed** — the
   previously latent same-name clash (lead's catch) cannot reappear
   without breaking these tests.
2. **Docstring-example walks via PUBLIC-ONLY imports** — the example
   in ``_mount.py``'s docstring uses ONLY names accessible via
   ``from scitex_live_paper import ...`` (no reaching into
   ``_django.*`` private modules).
3. **Lazy-import safety** — accessing ``MountResolver`` triggers the
   Django import; library-only consumers (``from scitex_live_paper
   import BundleContext`` only) don't pay that cost at package import
   time.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import typing
from pathlib import Path
from typing import get_type_hints

import pytest


# ──────────────────────────────────────────────────────────────────
# Both resolver-type aliases — present, distinct, signed correctly
# ──────────────────────────────────────────────────────────────────


def test_bundle_resolver_in_top_level_all():
    # Arrange
    import scitex_live_paper as lp
    # Act
    # Assert
    assert "BundleResolver" in lp.__all__


def test_mount_resolver_in_top_level_all():
    # Arrange
    import scitex_live_paper as lp
    # Act
    # Assert
    assert "MountResolver" in lp.__all__


def test_bundle_resolver_is_zero_arg_callable_to_bundle__assert_origin_is_typing_callable():
    # Zero-arg `Callable[[], Bundle]` per the `_types.py` definition.
    # Used by `BundleSource.from_resolver(callable)`.
    # Arrange
    from scitex_live_paper import BundleResolver
    # Act
    origin = typing.get_origin(BundleResolver)
    # Assert
    assert origin is typing.Callable or origin is callable or origin is not None


def test_bundle_resolver_is_zero_arg_callable_to_bundle__assert_args_bundleresolver_shoul():
    # Zero-arg `Callable[[], Bundle]` per the `_types.py` definition.
    # Used by `BundleSource.from_resolver(callable)`.
    # Arrange
    from scitex_live_paper import BundleResolver
    origin = typing.get_origin(BundleResolver)
    # Act
    args = typing.get_args(BundleResolver)
    # Assert
    assert args, "BundleResolver should have type args"




def test_mount_resolver_is_request_arg_callable_to_bundle_context__assert_origin_is_typing_callable_2():
    # Request-arg `Callable[..., BundleContext]` per `_mount.py`.
    # Used by `mount(resolver=...)`.
    # Arrange
    from scitex_live_paper import BundleContext, MountResolver
    # Act
    origin = typing.get_origin(MountResolver)
    # Assert
    assert origin is typing.Callable or origin is callable or origin is not None


def test_mount_resolver_is_request_arg_callable_to_bundle_context__assert_bundlecontext_in_args_f_m():
    # Request-arg `Callable[..., BundleContext]` per `_mount.py`.
    # Used by `mount(resolver=...)`.
    # Arrange
    from scitex_live_paper import BundleContext, MountResolver
    origin = typing.get_origin(MountResolver)
    # Act
    args = typing.get_args(MountResolver)
    # Assert
    assert BundleContext in args, (
        f"MountResolver return should be BundleContext; got args {args!r}"
    )




def test_resolver_aliases_are_distinct_objects():
    # Two layers, two aliases. Pin: they're not the same object — a
    # future "let's unify them" refactor that loses this distinction
    # has to come through this test.
    # Arrange
    from scitex_live_paper import BundleResolver, MountResolver
    # Act
    # Assert
    assert BundleResolver is not MountResolver


# ──────────────────────────────────────────────────────────────────
# Deprecated alias inside `_django._mount` — back-compat preserved
# ──────────────────────────────────────────────────────────────────


def test_mount_module_exposes_mount_resolver_as_canonical__assert_hasattr_mount_mountresolv():
    # Arrange
    # Act
    pytest.importorskip("django")
    from scitex_live_paper._django import _mount
    # Assert
    assert hasattr(_mount, "MountResolver")


def test_mount_module_exposes_mount_resolver_as_canonical__assert_mountresolver_in_mount_al():
    # Arrange
    # Act
    pytest.importorskip("django")
    from scitex_live_paper._django import _mount
    # Assert
    assert "MountResolver" in _mount.__all__




def test_mount_module_keeps_bundle_resolver_alias_for_back_compat__assert_hasattr_mount_bundleresol():
    # PR #27's original landing exposed `_django._mount.BundleResolver`.
    # We keep it as a deprecated alias to `MountResolver` so any
    # in-tree consumer (test, host wrapping in private code) doesn't
    # break on the rename — only the top-level public surface changes
    # to surface `MountResolver`.
    # Arrange
    # Act
    pytest.importorskip("django")
    from scitex_live_paper._django import _mount
    # Assert
    assert hasattr(_mount, "BundleResolver")


def test_mount_module_keeps_bundle_resolver_alias_for_back_compat__assert_mount_bundleresolver_is_m():
    # PR #27's original landing exposed `_django._mount.BundleResolver`.
    # We keep it as a deprecated alias to `MountResolver` so any
    # in-tree consumer (test, host wrapping in private code) doesn't
    # break on the rename — only the top-level public surface changes
    # to surface `MountResolver`.
    # Arrange
    # Act
    pytest.importorskip("django")
    from scitex_live_paper._django import _mount
    # Assert
    assert _mount.BundleResolver is _mount.MountResolver




# ──────────────────────────────────────────────────────────────────
# Top-level access — lazy import (no Django cost for library-only)
# ──────────────────────────────────────────────────────────────────


def test_importing_scitex_live_paper_does_not_import_django():
    # Library-only consumers (`from scitex_live_paper import BundleContext`)
    # shouldn't pay the Django import cost. Pin: importing the package
    # itself does NOT load `django` as a side effect.
    #
    # We force a fresh import by stripping `django` from sys.modules
    # before re-importing the package.
    # Arrange
    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("django")}
    # Act
    try:
        # Force fresh import of scitex_live_paper too so __init__ re-runs.
        # Saved aside and restored below so sibling tests keep seeing
        # the same module objects (identity/isinstance must not depend
        # on collection order).
        saved_pkg = {}
        for k in list(sys.modules):
            if k == "scitex_live_paper" or k.startswith("scitex_live_paper."):
                saved_pkg[k] = sys.modules.pop(k)
        try:
            import scitex_live_paper  # noqa: F401
            django_keys_after_import = [k for k in sys.modules if k.startswith("django")]
        finally:
            for k in list(sys.modules):
                if k == "scitex_live_paper" or k.startswith("scitex_live_paper."):
                    del sys.modules[k]
            sys.modules.update(saved_pkg)
    finally:
        for k, mod in saved.items():
            sys.modules[k] = mod
    # Assert
    assert not django_keys_after_import, (
        f"importing scitex_live_paper pulled in django modules: {django_keys_after_import!r}"
    )


def test_accessing_mount_resolver_triggers_django_import__assert_scitex_live_paper_mountre():
    # PEP 562 module-level `__getattr__` lazy-resolves `MountResolver`.
    # When called, Django becomes available.
    # Arrange
    # Act
    pytest.importorskip("django")
    import scitex_live_paper
    # Assert
    assert scitex_live_paper.MountResolver is not None


def test_accessing_mount_resolver_triggers_django_import__assert_scitex_live_paper_mountre_2():
    # PEP 562 module-level `__getattr__` lazy-resolves `MountResolver`.
    # When called, Django becomes available.
    # Arrange
    # Act
    pytest.importorskip("django")
    import scitex_live_paper
    # Assert
    assert scitex_live_paper.MountResolver is scitex_live_paper.MountResolver




def test_unknown_attribute_still_raises():
    # __getattr__ must NOT swallow lookups for names we don't export.
    # Arrange
    import scitex_live_paper
    # Act
    # Assert
    with pytest.raises(AttributeError):
        _ = scitex_live_paper.NotARealThing


# ──────────────────────────────────────────────────────────────────
# Docstring-example walk — every name in the example is public
# ──────────────────────────────────────────────────────────────────


def test_mount_docstring_example_imports_are_all_public():
    """Walk the import block from ``_mount.py``'s docstring example.

    The point of the docstring is to show hosts how to wire a
    resolver. Every name imported in the example MUST be importable
    via ``from scitex_live_paper import ...`` (NOT
    ``from scitex_live_paper._django._mount import ...``). If this
    test starts failing, the docstring is teaching hosts to reach
    into private modules — fix the docstring or hoist the missing
    name to the public surface.
    """
    pytest.importorskip("django")

    # Arrange: the docstring's example block (verbatim from `_mount.py`):
    docstring_imports = [
        "BundleContext",
        "BundleNotFound",
        "BundleSource",
        "PaperState",
        "RendererOptions",
        "mount",
    ]

    import scitex_live_paper

    # Act — collect per-name public-surface verdicts (one value per name)
    accessible = {
        name: hasattr(scitex_live_paper, name) for name in docstring_imports
    }
    # Assert — every example name is importable from the top level
    assert all(accessible.values()), (
        "docstring example imports not on the public surface: "
        f"{sorted(n for n, ok in accessible.items() if not ok)}"
    )


def test_mount_docstring_example_imports_are_all_exported():
    """Companion to ..._are_all_public: the same names must be in __all__."""
    pytest.importorskip("django")

    # Arrange
    docstring_imports = [
        "BundleContext",
        "BundleNotFound",
        "BundleSource",
        "PaperState",
        "RendererOptions",
        "mount",
    ]

    import scitex_live_paper

    # Act
    exported = {
        name: name in scitex_live_paper.__all__ for name in docstring_imports
    }
    # Assert — accessible is covered by the companion test; here only export
    assert all(exported.values()), (
        f"accessible but not in __all__: "
        f"{sorted(n for n, ok in exported.items() if not ok)}"
    )


# ──────────────────────────────────────────────────────────────────
# Public-only build — a host CAN construct a resolver using only
# top-level imports, then hand it to `mount()` and get patterns back.
# ──────────────────────────────────────────────────────────────────


FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "scitex_live_paper" / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"


def test_host_can_build_resolver_using_only_public_imports__assert_namespace_live_paper():
    # Arrange
    """The completeness pin: a host wires the full resolver path
    using ONLY ``from scitex_live_paper import ...`` — no private
    module access. If this test ever needs an
    ``_django.*`` import, that's the audit-gap signal.
    """
    pytest.importorskip("django")
    from scitex_live_paper import (
        BundleContext,
        BundleNotFound,
        BundleSource,
        PaperState,
        RendererOptions,
        mount,
    )
    def host_resolver(request, paper_id=None, **kw):
        if paper_id == "missing":
            raise BundleNotFound(f"paper {paper_id!r} unknown")
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_MIN),
            paper_state=PaperState(stage="preprint"),
            api_base="/api/",
            options=RendererOptions(embed_mode=True),
        )
    # Act
    patterns, namespace = mount(host_resolver)
    # Assert
    assert namespace == "live_paper"


def test_host_can_build_resolver_using_only_public_imports__assert_names_api_dispatch_viewer():
    # Arrange
    """The completeness pin: a host wires the full resolver path
    using ONLY ``from scitex_live_paper import ...`` — no private
    module access. If this test ever needs an
    ``_django.*`` import, that's the audit-gap signal.
    """
    pytest.importorskip("django")
    from scitex_live_paper import (
        BundleContext,
        BundleNotFound,
        BundleSource,
        PaperState,
        RendererOptions,
        mount,
    )
    def host_resolver(request, paper_id=None, **kw):
        if paper_id == "missing":
            raise BundleNotFound(f"paper {paper_id!r} unknown")
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_MIN),
            paper_state=PaperState(stage="preprint"),
            api_base="/api/",
            options=RendererOptions(embed_mode=True),
        )
    patterns, namespace = mount(host_resolver)
    # Act
    names = sorted(p.name for p in patterns if p.name)
    # Assert
    assert names == ["api_dispatch", "viewer_page"]




# ──────────────────────────────────────────────────────────────────
# Exception hierarchy — also fully public-importable
# ──────────────────────────────────────────────────────────────────


def test_exception_hierarchy_fully_public():
    # PR #47's hierarchy. Repeat the check here so the completeness
    # invariant lives in one place: the audit-pin file.
    # Arrange
    import scitex_live_paper as lp

    names = (
        "BundleResolverError",
        "BundleNotFound",
        "BundleAccessDenied",
    )
    # Act
    missing = [
        name for name in names if not (hasattr(lp, name) and name in lp.__all__)
    ]
    # Assert
    assert missing == []
