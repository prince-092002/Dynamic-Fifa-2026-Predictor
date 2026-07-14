import fs from "fs";
import path from "path";
import { buildPredictionHistoryDataset } from "@/features/prediction-history/lib/history";

const PROJECT_ROOT = path.join(process.cwd(), "..");
const HISTORY_DIR = path.join(PROJECT_ROOT, "data", "prediction_history");
const PUBLIC_DATA_DIR = path.join(PROJECT_ROOT, "public_data");

function readJson(file: string): unknown {
  try {
    return JSON.parse(fs.readFileSync(file, "utf-8"));
  } catch {
    return null;
  }
}

export function getPredictionHistoryData() {
  const manifest = readJson(path.join(HISTORY_DIR, "manifest.json"));
  const entries =
    manifest && typeof manifest === "object" && Array.isArray((manifest as { snapshots?: unknown[] }).snapshots)
      ? (manifest as { snapshots: Array<{ file?: unknown }> }).snapshots
      : [];
  const snapshotFiles: Record<string, unknown> = {};

  for (const entry of entries) {
    if (typeof entry.file !== "string") continue;
    const resolved = path.resolve(HISTORY_DIR, entry.file);
    const safePrefix = `${path.resolve(HISTORY_DIR)}${path.sep}`;
    if (!resolved.startsWith(safePrefix)) continue;
    snapshotFiles[entry.file] = readJson(resolved);
  }

  return buildPredictionHistoryDataset(
    manifest,
    snapshotFiles,
    readJson(path.join(PUBLIC_DATA_DIR, "knockout_bracket.json")),
    readJson(path.join(PUBLIC_DATA_DIR, "teams.json")),
  );
}
