import { eq } from "drizzle-orm";
import { db } from "../client";
import { elements } from "../schema";

export type Element = typeof elements.$inferSelect;
export type NewElement = Omit<typeof elements.$inferInsert, "id">;

export function findElementsBySource(sourceId: string): Element[] {
    return db.select().from(elements).where(eq(elements.sourceId, sourceId)).all();
}

export function insertElements(data: NewElement[]): void {
    if (data.length === 0) return;

    const rows = data.map((el) => ({ ...el, id: crypto.randomUUID() }));
    db.transaction(() => {
        for (const row of rows) {
            db.insert(elements).values(row).run();
        }
    });
}

export function deleteElementsBySource(sourceId: string): void {
    db.delete(elements).where(eq(elements.sourceId, sourceId)).run();
}