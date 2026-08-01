#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { resolve, relative, isAbsolute } from "node:path";

const baseUrl = (process.env.ES_URL || "").replace(/\/$/, "");
function fail(message) { console.error(`Error: ${message}`); process.exit(1); }
if (!baseUrl) fail("ES_URL is not set. Load the project .env file first.");

function headers(hasBody = false) {
  const output = { Accept: "application/json" };
  if (hasBody) output["Content-Type"] = "application/json";
  if (process.env.ES_API_KEY) output.Authorization = `ApiKey ${process.env.ES_API_KEY}`;
  else if (process.env.ES_USERNAME || process.env.ES_PASSWORD) {
    if (!process.env.ES_USERNAME || !process.env.ES_PASSWORD) fail("Set both ES_USERNAME and ES_PASSWORD.");
    output.Authorization = `Basic ${Buffer.from(`${process.env.ES_USERNAME}:${process.env.ES_PASSWORD}`).toString("base64")}`;
  }
  return output;
}

async function jsonFile(file) {
  if (!file) return undefined;
  const root = process.cwd();
  const full = resolve(root, file);
  const rel = relative(root, full);
  if (isAbsolute(rel) || rel.startsWith("..")) fail("Body file must stay inside the workspace.");
  if (!file.endsWith(".json")) fail("Body must be a .json file.");
  try { return JSON.parse(await readFile(full, "utf8")); }
  catch (error) { fail(`Cannot read JSON body: ${error.message}`); }
}

function isReadOnly(method, path) {
  if (method === "GET" || method === "HEAD") return true;
  return method === "POST" && /\/(?:_search|_msearch|_count|_validate\/query|_explain(?:\/[^/]+)?)\/?(?:\?.*)?$/.test(path);
}

async function request(method, path, body) {
  method = method.toUpperCase();
  if (!path.startsWith("/") || path.startsWith("//")) fail("Path must start with one slash.");
  if (!isReadOnly(method, path) && process.env.ES_ALLOW_WRITES !== "1") {
    fail(`${method} ${path} may mutate Elasticsearch. Set ES_ALLOW_WRITES=1 for this intentional command.`);
  }
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: headers(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
    redirect: "error",
    signal: AbortSignal.timeout(60_000),
  });
  const text = await response.text();
  let payload;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }
  if (!response.ok) {
    const detail = payload?.error?.reason || payload?.error?.type || String(payload).slice(0, 2000);
    fail(`Elasticsearch ${response.status} ${response.statusText}: ${detail}`);
  }
  console.log(typeof payload === "string" ? payload : JSON.stringify(payload, null, 2));
}

const [command, first, second] = process.argv.slice(2);
switch (command) {
  case "health": await request("GET", "/_cluster/health"); break;
  case "search":
    if (!first || !second) fail("Usage: es.mjs search <index> <query.json>");
    if (!/^[a-zA-Z0-9._*-]+$/.test(first)) fail("Invalid index expression.");
    await request("POST", `/${first}/_search`, await jsonFile(second));
    break;
  case "request":
    if (!first || !second) fail("Usage: es.mjs request <method> <path> [body.json]");
    await request(first, second, await jsonFile(process.argv[5]));
    break;
  default: fail("Usage: es.mjs <health|search|request> ...");
}
