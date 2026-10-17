# mermaid vendored bundle (Django SPA surface)

`mermaid.min.js` is an **unmodified copy** of the official
[`mermaid`](https://www.npmjs.com/package/mermaid) v10.9.4 UMD build,
mirroring `src/scitex_live_paper/_renderer/assets/mermaid/`.

The Django SPA (`viewer.html` / `viewer_embed.html`) loads it with a
plain `<script>` tag so the claim DAG pane renders offline with no
CDN — the same self-contained boundary the static renderer keeps.
Loaded as a classic script (UMD global `window.mermaid`), NOT as an
ES module; `claim-details.js` feature-detects `window.mermaid` and
falls back to mermaid source text when absent.

Licence: MIT (see [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid)).
