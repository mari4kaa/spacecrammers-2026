// Written with AI assistance (Claude, Anthropic) for InfoFlame, NASA Space Apps Challenge 2026, team Spacecrammers. See AI_USE.md.
// Reads GEMINI_API_KEY from worker/.env and stores it as an encrypted Cloudflare secret.
// The key is passed to wrangler on stdin, so it never appears in your shell history or in git.
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

let env;
try { env = readFileSync(new URL("../.env", import.meta.url), "utf8"); }
catch { console.error("worker/.env not found. Create it with one line: GEMINI_API_KEY=your-key"); process.exit(1); }
const m = env.match(/^\s*GEMINI_API_KEY\s*=\s*["']?([^"'\s#]+)["']?/m);
if (!m) { console.error("worker/.env has no GEMINI_API_KEY=... line"); process.exit(1); }
const r = spawnSync("npx", ["wrangler", "secret", "put", "GEMINI_API_KEY"], { input: m[1] + "\n", stdio: ["pipe", "inherit", "inherit"] });
process.exit(r.status ?? 1);
