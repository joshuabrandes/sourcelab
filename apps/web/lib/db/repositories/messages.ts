import { eq } from "drizzle-orm";
import { db } from "../client";
import { messages } from "../schema";

export type Message = typeof messages.$inferSelect;
export type NewMessage = Omit<typeof messages.$inferInsert, "id" | "createdAt">;
export type MessageRole = "user" | "assistant" | "system";

export function listMessagesByConversation(conversationId: string): Message[] {
    return db.select().from(messages).where(eq(messages.conversationId, conversationId)).all();
}

export function createMessage(data: NewMessage): Message {
    return db
        .insert(messages)
        .values({ ...data, id: crypto.randomUUID() })
        .returning()
        .get();
}

export function deleteMessagesByConversation(conversationId: string): void {
    db.delete(messages).where(eq(messages.conversationId, conversationId)).run();
}