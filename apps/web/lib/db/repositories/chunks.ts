import { eq } from "drizzle-orm";
import { db } from "../client";
import { chunks } from "../schema";

export type Chunk = typeof chunks.$inferSelect;
export type NewChunk = Omit<typeof chunks.$inferInsert, "id">;

export function findChunkById(id: string): Chunk | undefined {
    return db.select().from(chunks).where(eq(chunks.id, id)).get();
}

export function findChunksByIds(ids: string[]): Chunk[] {
    if (ids.length === 0) return [];
    return db.select().from(chunks).all().filter((c) => ids.includes(c.id));
}

export function listChunksBySource(sourceId: string): Chunk[] {
    return db.select().from(chunks).where(eq(chunks.sourceId, sourceId)).all();
}

export function insertChunks(data: NewChunk[]): Chunk[] {
    if (data.length === 0) return [];

    const rows = data.map((chunk) => ({ ...chunk, id: crypto.randomUUID() }));
    return db.transaction(() =>
        rows.map((row) => db.insert(chunks).values(row).returning().get()),
    );
}

export function deleteChunksBySource(sourceId: string): void {
    db.delete(chunks).where(eq(chunks.sourceId, sourceId)).run();
}