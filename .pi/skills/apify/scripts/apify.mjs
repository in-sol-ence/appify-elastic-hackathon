#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { resolve, relative, isAbsolute } from "node:path";

const baseUrl = (process.env.APIFY_API_BASE_URL || "https://api.apify.com/v2").replace(/\/$/, "");
const token = process.env.APIFY_TOKEN;

function fail(message) {
  console.error(`Error: ${message}`);
  process.exit(1);
}

if (!token) fail("APIFY_TOKEN is not set. Load the project .env file first.");

function apiPath(value) {
  return encodeURIComponent(value).replace(/%7E/gi, "~");
}

async function inputFrom(file) {
  if (!file) return {};
  const root = process.cwd();
  const full = resolve(root, file);
  const rel = relative(root, full);
  if (isAbsolute(rel) || rel.startsWith("..")) fail("Input file must stay inside the workspace.");
  if (!file.endsWith(".json")) fail("Actor input must be a .json file.");
  try {
    return JSON.parse(await readFile(full, "utf8"));
  } catch (error) {
    fail(`Cannot read JSON input: ${error.message}`);
  }
}

async function request(path, { method = "GET", body } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(310_000),
  });
  const text = await response.text();
  let payload;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }
  if (!response.ok) {
    const detail = payload?.error?.message || payload?.message || String(payload).slice(0, 1000);
    fail(`Apify ${response.status} ${response.statusText}: ${detail}`);
  }
  return payload?.data ?? payload;
}

const [command, id, arg] = process.argv.slice(2);
if (!command || !id) {
  fail("Usage: apify.mjs <actor|run|run-sync|run-status|dataset-items> <id> [input.json|limit]");
}

let result;
switch (command) {
  case "actor":
    result = await request(`/acts/${apiPath(id)}`);
    break;
  case "run":
    result = await request(`/acts/${apiPath(id)}/runs`, { method: "POST", body: await inputFrom(arg) });
    break;
  case "run-sync":
    result = await request(`/acts/${apiPath(id)}/run-sync-get-dataset-items?timeout=300`, {
      method: "POST",
      body: await inputFrom(arg),
    });
    break;
  case "run-status":
    result = await request(`/actor-runs/${apiPath(id)}`);
    break;
  case "dataset-items": {
    const limit = arg === undefined ? 100 : Number(arg);
    if (!Number.isInteger(limit) || limit < 1 || limit > 1000) fail("limit must be an integer from 1 to 1000.");
    result = await request(`/datasets/${apiPath(id)}/items?clean=true&format=json&limit=${limit}`);
    break;
  }
  default:
    fail(`Unknown command: ${command}`);
}

console.log(JSON.stringify(result, null, 2));
