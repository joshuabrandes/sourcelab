import { eq } from "drizzle-orm";
import { db } from "../client";
import { elements } from "../schema";

export type Element = typeof elements.$inferSelect;
export type NewElement = Omit<typeof elements.$inferInsert, "id">;

export function findElementsBySource(sourceId: string): Element[] {
    return db.select().from(elements).where(eq(elements.sourceId, sourceId)).all();
}

export function insertElements(data: NewElement[]): Element[] {
    if (data.length === 0) return [];

    const rows = data.map((el) => ({ ...el, id: crypto.randomUUID() }));
    return db.transaction((tx) =>
        rows.map((row) => tx.insert(elements).values(row).returning().get()),
    );
}

export function deleteElementsBySource(sourceId: string): void {
    db.delete(elements).where(eq(elements.sourceId, sourceId)).run();
}
