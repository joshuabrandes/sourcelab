import { eq, sql } from "drizzle-orm";
import { db } from "../client";
import { sources } from "../schema";

export type Source = typeof sources.$inferSelect;
export type NewSource = Omit<typeof sources.$inferInsert, "id" | "createdAt">;
export type SourceStatus = "pending" | "processing" | "ready" | "error";

export function findSourceById(id: string): Source | undefined {
    return db.select().from(sources).where(eq(sources.id, id)).get();
}

export function listSourcesByProject(projectId: string): Source[] {
    return db.select().from(sources).where(eq(sources.projectId, projectId)).all();
}

export function createSource(data: NewSource): Source {
    return db
        .insert(sources)
        .values({ ...data, id: crypto.randomUUID() })
        .returning()
        .get();
}

export function updateSourceStatus(
    id: string,
    status: SourceStatus,
    extra?: { errorMessage?: string; tokenCount?: number; chunkCount?: number },
): Source | undefined {
    const processedAt = status === "ready" || status === "error"
        ? sql`(datetime('now'))`
        : undefined;

    return db
        .update(sources)
        .set({ status, processedAt, ...extra })
        .where(eq(sources.id, id))
        .returning()
        .get();
}

export function deleteSource(id: string): void {
    db.delete(sources).where(eq(sources.id, id)).run();
}