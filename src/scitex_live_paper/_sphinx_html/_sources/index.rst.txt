SciTeX Live Paper
=================

Live Paper provides scientific reading interfaces over a reusable PDF and
feed component. The architecture explains the boundaries between the viewer,
evidence, authoring, computation, and publication packages.

.. toctree::
   :maxdepth: 2

   architecture
   cli_reference

Interfaces
----------

.. list-table::
   :header-rows: 1

   * - Interface
     - Entry point
   * - Python API
     - ``scitex_live_paper`` bundle, context, rendering, and mount APIs
   * - CLI
     - ``scitex-live-paper``
   * - MCP
     - Agent tools through the ``mcp`` extra
   * - Skills
     - Packaged ``scitex-live-paper`` skill and architecture guide
   * - HTTP API
     - Authorized Django mount through the ``server`` extra
