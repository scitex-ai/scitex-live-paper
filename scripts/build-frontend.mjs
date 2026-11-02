/** Bundle the native adapter and its local module graph for cache coherence. */
import { build } from "esbuild";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../src/scitex_live_paper/_django/static/live_paper/js/", import.meta.url));
await build({ entryPoints: [root + "viewer.js"], outfile: root + "viewer-entry.js", bundle: true, format: "esm", platform: "browser", banner: { js: "/* GENERATED from viewer.js: npm run build:frontend. Do not edit. */" } });
