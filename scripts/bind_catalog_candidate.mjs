#!/usr/bin/env node

import { appendFile, readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const EXPECTED_WORKER = "liquilens-ai-catalog";
const SHA_PATTERN = /^[0-9a-f]{40}$/u;
const VERSION_ID_PATTERN = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/u;

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be one JSON object`);
  }
  return value;
}

function parseJson(text, label) {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
}

export function extractCandidateId(receiptText) {
  if (typeof receiptText !== "string" || receiptText.trim() === "") {
    throw new Error("Wrangler upload receipt is empty");
  }
  const rows = receiptText
    .split(/\r?\n/u)
    .filter((line) => line.trim() !== "")
    .map((line, index) =>
      requireObject(parseJson(line, `Wrangler receipt row ${index + 1}`), `Wrangler receipt row ${index + 1}`),
    );
  const uploads = rows.filter((row) => row.type === "version-upload");
  if (uploads.length !== 1) {
    throw new Error(`Wrangler emitted ${uploads.length} candidate version receipts; expected exactly one`);
  }
  const upload = uploads[0];
  if (!VERSION_ID_PATTERN.test(upload.version_id ?? "")) {
    throw new Error("Wrangler candidate version ID is not a canonical lowercase UUID");
  }
  if (upload.worker_name !== EXPECTED_WORKER || upload.worker_name_overridden !== false) {
    throw new Error("Wrangler candidate receipt names the wrong or overridden Worker");
  }
  return upload.version_id;
}

export function bindCatalogCandidate({ receiptText, versionText, expectedSha }) {
  if (!SHA_PATTERN.test(expectedSha ?? "")) {
    throw new Error("Expected GitHub SHA must be 40 lowercase hexadecimal characters");
  }
  const versionId = extractCandidateId(receiptText);
  const version = requireObject(
    parseJson(versionText, "Cloudflare candidate version metadata"),
    "Cloudflare candidate version metadata",
  );
  const metadata = requireObject(version.metadata, "Cloudflare candidate metadata");
  const annotations = requireObject(
    version.annotations,
    "Cloudflare candidate annotations",
  );
  if (version.id !== versionId) {
    throw new Error("Cloudflare candidate metadata ID differs from the upload receipt");
  }
  if (metadata.source !== "wrangler") {
    throw new Error("Cloudflare candidate metadata has an unexpected source");
  }
  if (annotations["workers/tag"] !== expectedSha) {
    throw new Error("Cloudflare candidate tag differs from the exact GitHub SHA");
  }
  if (annotations["workers/message"] !== `GitHub-${expectedSha}`) {
    throw new Error("Cloudflare candidate message differs from the exact GitHub SHA");
  }
  if (annotations["workers/triggered_by"] !== "version_upload") {
    throw new Error("Cloudflare candidate was not created by a version upload");
  }
  return versionId;
}

async function main(args) {
  const [mode, ...paths] = args;
  if (mode === "extract" && paths.length === 2) {
    const [receiptPath, outputPath] = paths;
    const versionId = extractCandidateId(await readFile(receiptPath, "utf8"));
    await writeFile(outputPath, `${versionId}\n`, {
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
    return;
  }
  if (mode === "bind" && paths.length === 4) {
    const [receiptPath, versionPath, expectedSha, githubOutputPath] = paths;
    const versionId = bindCatalogCandidate({
      receiptText: await readFile(receiptPath, "utf8"),
      versionText: await readFile(versionPath, "utf8"),
      expectedSha,
    });
    await appendFile(githubOutputPath, `version_id=${versionId}\n`, "utf8");
    return;
  }
  throw new Error(
    "usage: bind_catalog_candidate.mjs extract RECEIPT ID_OUTPUT | bind RECEIPT VERSION SHA GITHUB_OUTPUT",
  );
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
