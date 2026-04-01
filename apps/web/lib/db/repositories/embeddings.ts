import { sqlite } from "../client";

// sqlite-vec binds Float32Array as a blob — serialize once, reuse the statement
function toBlob(embedding: number[]): Buffer {
    return Buffer.from(new Float32Array(embedding).buffer);
}

const stmtUpsert = sqlite.prepare(
    "INSERT OR REPLACE INTO chunk_embeddings(chunk_id, embedding) VALUES (?, ?)",
);

const stmtDelete = sqlite.prepare(
    "DELETE FROM chunk_embeddings WHERE chunk_id = ?",
);

export type VectorMatch = { chunkId: string; distance: number };

export function upsertEmbedding(chunkId: string, embedding: number[]): void {
    stmtUpsert.run(chunkId, toBlob(embedding));
}

export function upsertEmbeddings(entries: { chunkId: string; embedding: number[] }[]): void {
    const tx = sqlite.transaction(() => {
        for (const { chunkId, embedding } of entries) {
            stmtUpsert.run(chunkId, toBlob(embedding));
        }
    });
    tx();
}

export function findNearestChunks(embedding: number[], k: number): VectorMatch[] {
    const stmt = sqlite.prepare<[Buffer, number], { chunk_id: string; distance: number }>(`
        SELECT chunk_id, distance
        FROM chunk_embeddings
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
    `);
    return stmt.all(toBlob(embedding), k).map(({ chunk_id, distance }) => ({
        chunkId: chunk_id,
        distance,
    }));
}

export function deleteEmbedding(chunkId: string): void {
    stmtDelete.run(chunkId);
}

export function deleteEmbeddingsByChunks(chunkIds: string[]): void {
    const tx = sqlite.transaction(() => {
        for (const id of chunkIds) {
            stmtDelete.run(id);
        }
    });
    tx();
}