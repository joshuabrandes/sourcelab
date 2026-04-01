import { eq, sql } from "drizzle-orm";
import { db } from "../client";
import { conversations } from "../schema";

export type Conversation = typeof conversations.$inferSelect;
export type NewConversation = Omit<typeof conversations.$inferInsert, "id" | "createdAt" | "updatedAt">;

export function findConversationById(id: string): Conversation | undefined {
    return db.select().from(conversations).where(eq(conversations.id, id)).get();
}

export function listConversationsByProject(projectId: string): Conversation[] {
    return db.select().from(conversations).where(eq(conversations.projectId, projectId)).all();
}

export function createConversation(data: NewConversation): Conversation {
    return db
        .insert(conversations)
        .values({ ...data, id: crypto.randomUUID() })
        .returning()
        .get();
}

export function updateConversationTitle(id: string, title: string): Conversation | undefined {
    return db
        .update(conversations)
        .set({ title, updatedAt: sql`(datetime('now'))` })
        .where(eq(conversations.id, id))
        .returning()
        .get();
}

export function deleteConversation(id: string): void {
    db.delete(conversations).where(eq(conversations.id, id)).run();
}