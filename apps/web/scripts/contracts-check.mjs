/**
 * Contract freshness gate (R6-01).
 *
 * Fails (exit 1) when the committed generated OpenAPI TS types are stale relative
 * to `contracts/openapi.json` — i.e. when `npm run contracts:generate` would change
 * the output. This mirrors the Python-side `scripts/verify_openapi_up_to_date.py`
 * (which checks `openapi.json` vs the FastAPI app) and closes the drift gap that let
 * `src/types/generated/openapi.d.ts` fall behind the contract.
 *
 * Pure-Node, offline, read-only: regenerates to stdout and compares; never writes.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const contract = path.resolve(webRoot, "..", "..", "contracts", "openapi.json");
const committed = path.resolve(webRoot, "src", "types", "generated", "openapi.d.ts");
const cli = path.resolve(webRoot, "node_modules", "openapi-typescript", "bin", "cli.js");

const normalize = (s) => s.replaceAll("\r\n", "\n").trimEnd();

let generated;
try {
  generated = execFileSync(process.execPath, [cli, contract], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
} catch (err) {
  console.error(`contracts:check — failed to regenerate types from ${contract}`);
  console.error(String(err?.message ? err.message : err));
  process.exit(2);
}

let onDisk;
try {
  onDisk = readFileSync(committed, "utf8");
} catch {
  console.error(`contracts:check — committed types not found: ${committed}`);
  console.error("Run: npm run contracts:generate");
  process.exit(1);
}

if (normalize(generated) !== normalize(onDisk)) {
  console.error("contracts:check — src/types/generated/openapi.d.ts is STALE vs contracts/openapi.json.");
  console.error("Run: npm run contracts:generate  (and commit the result).");
  process.exit(1);
}

console.log("contracts:check — openapi.d.ts is in sync with contracts/openapi.json.");
