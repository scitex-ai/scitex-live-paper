---
description: |
  [TOPIC] Paper workflow architecture
  [DETAILS] Use when deciding package ownership, embedding Live Paper, changing content or action contracts, or connecting computation and provenance to the PDF/feed. Read the shared architecture reference for application, UI component, library, and connector boundaries.
tags: [scitex-live-paper-architecture]
---

# Paper workflow architecture

Read [the canonical architecture](references/architecture.md) before changing cross-package integration. This same Markdown source is included by Sphinx; update it when the architecture changes.

Route generic PDF/feed behavior to Rich PDF, scientific presentation and orchestration to Live Paper, claim/provenance authority to Clew, and host authorization and persistence to the host connector. Scholar and Writer embed the Live Paper component. Stats owns numerical results and verification; the execution host owns authorized jobs.

Distinguish an application shell from a reusable UI component or core library. GUI, CLI, TUI, and API describe access interfaces. Diagram arrows mean consumer uses provider; describe artifact flow as a workflow.

The Rich PDF extraction and richer embedding contracts are target design. Check the reference's implementation sequence and the actual public API before assuming they exist. Preserve current adapters while introducing those interfaces.

For documentation changes, build with `make -C docs/sphinx html`. Before packaging a release, refresh the shipped HTML with `make -C docs/sphinx bundle` and verify the architecture source, guide, HTML, and local diagram assets are in the wheel and sdist.
