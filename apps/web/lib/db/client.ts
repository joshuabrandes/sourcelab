import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as sqliteVec from "sqlite-vec";
import * as schema from "./schema";
import path from "node:path";

const DB_PATH = path.join(process.cwd(), "../../data/sourcelab.db");

export const EMBEDDING_DIM = 768; // nomic-embed-text default

const sqlite = new Database(DB_PATH);

sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

sqliteVec.load(sqlite);

sqlite.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[${EMBEDDING_DIM}]
  )
`);

export const db = drizzle(sqlite, { schema });
export { sqlite };
