#!/usr/bin/env node
const apifyBase = (process.env.APIFY_API_BASE_URL || "https://api.apify.com/v2").replace(/\/$/, "");
const esBase = (process.env.ES_URL || "").replace(/\/$/, "");
const apifyToken = process.env.APIFY_TOKEN;
const [datasetId, index, idField] = process.argv.slice(2);

function fail(message) { console.error(`Error: ${message}`); process.exit(1); }
if (!apifyToken) fail("APIFY_TOKEN is not set.");
if (!esBase) fail("ES_URL is not set.");
if (process.env.ES_ALLOW_WRITES !== "1") fail("Set ES_ALLOW_WRITES=1 for this intentional ingestion.");
if (!datasetId || !index) fail("Usage: ingest.mjs <dataset-id> <index> [id-field]");
if (!/^[a-z0-9._-]+$/.test(index)) fail("Index must use lowercase letters, digits, dots, underscores, or hyphens.");
if (idField && !/^[A-Za-z0-9_.-]+$/.test(idField)) fail("Invalid ID field.");
const batchSize = Number(process.env.PIPELINE_BATCH_SIZE || 500);
if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > 1000) fail("PIPELINE_BATCH_SIZE must be 1–1000.");

function esHeaders() {
  const result = { Accept: "application/json", "Content-Type": "application/x-ndjson" };
  if (process.env.ES_API_KEY) result.Authorization = `ApiKey ${process.env.ES_API_KEY}`;
  else if (process.env.ES_USERNAME || process.env.ES_PASSWORD) {
    if (!process.env.ES_USERNAME || !process.env.ES_PASSWORD) fail("Set both ES_USERNAME and ES_PASSWORD.");
    result.Authorization = `Basic ${Buffer.from(`${process.env.ES_USERNAME}:${process.env.ES_PASSWORD}`).toString("base64")}`;
  }
  return result;
}

function valueAt(item, path) {
  return path.split(".").reduce((value, key) => value?.[key], item);
}

async function apifyPage(offset) {
  const url = `${apifyBase}/datasets/${encodeURIComponent(datasetId)}/items?clean=true&format=json&offset=${offset}&limit=${batchSize}`;
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${apifyToken}`, Accept: "application/json" },
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) fail(`Apify dataset request failed: ${response.status} ${await response.text()}`);
  return response.json();
}

async function indexBatch(items) {
  const lines = [];
  for (const item of items) {
    const metadata = { _index: index };
    if (idField) {
      const id = valueAt(item, idField);
      if (!["string", "number", "boolean"].includes(typeof id)) fail(`Item is missing scalar ID field '${idField}'.`);
      metadata._id = String(id);
    }
    lines.push(JSON.stringify({ index: metadata }), JSON.stringify(item));
  }
  const response = await fetch(`${esBase}/_bulk`, {
    method: "POST",
    headers: esHeaders(),
    body: `${lines.join("\n")}\n`,
    redirect: "error",
    signal: AbortSignal.timeout(120_000),
  });
  const text = await response.text();
  if (!response.ok) fail(`Elasticsearch bulk request failed: ${response.status} ${text.slice(0, 2000)}`);
  let result;
  try { result = JSON.parse(text); } catch { fail("Elasticsearch returned non-JSON bulk output."); }
  if (result.errors) {
    const failures = result.items
      .map((entry, i) => ({ i, ...(entry.index || entry.create || entry.update || entry.delete) }))
      .filter((entry) => entry.error)
      .slice(0, 5);
    fail(`Bulk indexing had item errors: ${JSON.stringify(failures)}`);
  }
}

let offset = 0;
while (true) {
  const items = await apifyPage(offset);
  if (!Array.isArray(items)) fail("Apify dataset response was not an array.");
  if (items.length === 0) break;
  await indexBatch(items);
  offset += items.length;
  console.error(`Indexed ${offset} item(s)...`);
  if (items.length < batchSize) break;
}
console.log(JSON.stringify({ datasetId, index, indexed: offset, idField: idField || null }, null, 2));
