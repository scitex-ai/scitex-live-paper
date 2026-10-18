# Consumer integration guide — `scitex_live_paper` as an SDK

The core never imports a consumer. Each host mounts the Django app with
its own resolver and injects its own renderer adapters through the
`figure` / `snippet` / `claim-graph` ports. Three integration moves:

## 1. Mount with a resolver

```python
from django.urls import include, path
from scitex_live_paper import (
    BundleContext, BundleNotFound, BundleSource, PaperState, mount,
)

def my_resolver(request, paper_id, **url_kwargs) -> BundleContext:
    row = load_paper(paper_id, request.user.current_project.id)
    if row is None:
        raise BundleNotFound(paper_id)
    return BundleContext(
        source=BundleSource.from_dir(row.bundle_path),
        paper_state=PaperState(stage="accepted", ...),
        api_base=f"/apps/live-paper/{paper_id}/api/",
    )

urlpatterns = [
    path("apps/live-paper/<paper_id>/", include(mount(resolver=my_resolver))),
]
```

`mount()` calls the resolver per request, stashes the result on
`request.live_paper_context`, and maps `BundleNotFound → 404`,
`BundleAccessDenied → 403`. No caching at the mount layer — the
resolver is the cache point. Importing `scitex_live_paper` alone never
loads Django (lazy `MountResolver`); hosts that only need the library
surface skip the `[django]` extra.

## 2. Inject adapters (two roads, same contract)

Direct-passing (simplest; what the standalone server does):

```python
from scitex_live_paper.ports import Registry, FigzFigureAdapter

registry = Registry()
registry.register("figure", FigzFigureAdapter())  # PortNotFound when absent
```

Distribution (for renderer packages shared across hosts) — publish
under the `scitex.livepaper.renderers` group; each entry point's
object exposes `port` + `adapter` (+ optional `name`):

```toml
[project.entry-points."scitex.livepaper.renderers"]
figz-default = "my_renderers:FigzDefaultEntry"
```

```python
from scitex_live_paper.ports import discover, Registry

registry = Registry()
for port, name, adapter in discover():
    registry.register(port, adapter, name=name)
```

Hand the populated registry inside the resolver-built
`BundleContext.renderers`; `api/port/...` 404s cleanly when empty.

## 3. Prove it with the conformance kit

```python
from scitex_live_paper.ports import check_entry_point, check_figure_fragment

def test_our_adapters_conform(bundle):
    # Arrange — our injected adapters
    from my_renderers import MyFigureEntry
    # Act
    port, name, adapter = check_entry_point(MyFigureEntry)
    fragment = adapter.render_figure(bundle, "fig-1", {})
    # Assert
    check_figure_fragment(fragment, "fig-1")
```

One green run per consumer is the integration gate.

## Per-consumer notes

| Consumer | Uses | Notes |
|---|---|---|
| `scitex-agentic-journal` | claim-graph port + `ReReviewBadge` types | badge verdicts flow journal → paper; journal never imports the viewer |
| hub PDF viewer | `mount()` + figure overlay slot | viewer shell is the first injector; overlay strips on print/export |
| `scitex-writer` `_django` | read-only embed (`?embed=1` shell) | authoring preview reuses the renderer, no fork |
| `scitex-scholar` `_django` | reading surface | same mount, scholar-owned resolver (access policy) |
