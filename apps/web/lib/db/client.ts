import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import * as sqliteVec from "sqlite-vec";
import * as schema from "./schema";
import path from "node:path";

const DB_PATH = path.join(process.cwd(), "../../data/sourcelab.db");

export const EMBEDDING_DIM = 2560; // qwen3-embedding:4b default output size

const sqlite = new Database(DB_PATH);

sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

sqliteVec.load(sqlite);

sqlite.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding FLOAT[${EMBEDDING_DIM}]
  );

  CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    chunk_id UNINDEXED,
    source_id UNINDEXED,
    source_title,
    content,
    heading_context,
    tokenize = 'unicode61 remove_diacritics 2'
  );

  CREATE TRIGGER IF NOT EXISTS chunks_ai_fts
  AFTER INSERT ON chunks
  BEGIN
    INSERT INTO chunk_fts (chunk_id, source_id, source_title, content, heading_context)
    SELECT
      NEW.id,
      NEW.source_id,
      COALESCE(s.title, ''),
      NEW.content,
      COALESCE(NEW.heading_context, '')
    FROM sources AS s
    WHERE s.id = NEW.source_id;
  END;

  CREATE TRIGGER IF NOT EXISTS chunks_ad_fts
  AFTER DELETE ON chunks
  BEGIN
    DELETE FROM chunk_fts WHERE chunk_id = OLD.id;
  END;

  CREATE TRIGGER IF NOT EXISTS chunks_au_fts
  AFTER UPDATE ON chunks
  BEGIN
    DELETE FROM chunk_fts WHERE chunk_id = OLD.id;
    INSERT INTO chunk_fts (chunk_id, source_id, source_title, content, heading_context)
    SELECT
      NEW.id,
      NEW.source_id,
      COALESCE(s.title, ''),
      NEW.content,
      COALESCE(NEW.heading_context, '')
    FROM sources AS s
    WHERE s.id = NEW.source_id;
  END;

  CREATE TRIGGER IF NOT EXISTS sources_au_chunk_fts
  AFTER UPDATE OF title ON sources
  BEGIN
    DELETE FROM chunk_fts
    WHERE source_id = NEW.id;

    INSERT INTO chunk_fts (chunk_id, source_id, source_title, content, heading_context)
    SELECT
      c.id,
      c.source_id,
      COALESCE(NEW.title, ''),
      c.content,
      COALESCE(c.heading_context, '')
    FROM chunks AS c
    WHERE c.source_id = NEW.id;
  END;

  INSERT INTO chunk_fts (chunk_id, source_id, source_title, content, heading_context)
  SELECT
    c.id,
    c.source_id,
    COALESCE(s.title, ''),
    c.content,
    COALESCE(c.heading_context, '')
  FROM chunks AS c
  INNER JOIN sources AS s ON s.id = c.source_id
  WHERE NOT EXISTS (
    SELECT 1
    FROM chunk_fts AS f
    WHERE f.chunk_id = c.id
  );
`);

export const db = drizzle(sqlite, { schema });
export { sqlite };
