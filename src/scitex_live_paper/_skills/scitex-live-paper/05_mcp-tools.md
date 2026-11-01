---
description: |
  [TOPIC] MCP and skills
  [DETAILS] Source-backed LivePaper mcp and skills.
tags: [scitex-live-paper-mcp-tools]
---

# MCP and skills

With `[mcp]` installed, `scitex-live-paper mcp list-tools --json` reports the
registered projections and `mcp start` starts the stdio server. Tool functions
in `_mcp_server.py` delegate to real bundle/graph/port functions.

Call `live_paper_skills_list()` to enumerate installed Markdown resources,
then `live_paper_skills_get(name)` for a listed stem, including `SKILL` for the
entry point. These tools read this package's installed `_skills/` directory;
they do not depend on a repository checkout or a separate manual skill copy.
An unknown name raises an explicit error. Skill availability alone does not
prove a particular agent runner has loaded/discovered the installed package.
