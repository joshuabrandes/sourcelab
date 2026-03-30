import {sql} from "drizzle-orm";
import {index, integer, sqliteTable, text,} from "drizzle-orm/sqlite-core";

export const projects = sqliteTable("projects", {
    id: text("id").primaryKey(),
    name: text("name").notNull(),
    description: text("description"),
    systemPrompt: text("system_prompt"),
    modelId: text("model_id").default("llama3.1:8b"),
    embeddingModel: text("embedding_model").default("nomic-embed-text"),
    chunkSize: integer("chunk_size").default(512),
    chunkOverlap: integer("chunk_overlap").default(64),
    topK: integer("top_k").default(10),
    rerankTopN: integer("rerank_top_n").default(5),
    createdAt: text("created_at").default(sql`(datetime('now'))`),
    updatedAt: text("updated_at").default(sql`(datetime('now'))`),
});

export const sources = sqliteTable("sources", {
    id: text("id").primaryKey(),
    projectId: text("project_id").notNull().references(() => projects.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    contentType: text("content_type").notNull(),
    originalPath: text("original_path"),
    sourceUrl: text("source_url"),
    language: text("language"),
    metadata: text("metadata"), // JSON blob
    status: text("status").default("pending"),
    errorMessage: text("error_message"),
    tokenCount: integer("token_count"),
    chunkCount: integer("chunk_count"),
    createdAt: text("created_at").default(sql`(datetime('now'))`),
    processedAt: text("processed_at"),
}, (t) => [
    index("idx_sources_project").on(t.projectId),
]);

export const elements = sqliteTable("elements", {
    id: text("id").primaryKey(),
    sourceId: text("source_id").notNull().references(() => sources.id, { onDelete: "cascade" }),
    type: text("type").notNull(),
    level: integer("level"),
    content: text("content").notNull(),
    page: integer("page"),
    position: integer("position").notNull(),
    metadata: text("metadata"),         // JSON blob
}, (t) => [
    index("idx_elements_source").on(t.sourceId),
]);

export const chunks = sqliteTable("chunks", {
    id: text("id").primaryKey(),
    sourceId: text("source_id").notNull().references(() => sources.id, { onDelete: "cascade" }),
    content: text("content").notNull(),
    tokenCount: integer("token_count").notNull(),
    startElement: text("start_element").references(() => elements.id),
    endElement: text("end_element").references(() => elements.id),
    headingContext: text("heading_context"),
    page: integer("page"),
    position: integer("position").notNull(),
}, (t) => [
    index("idx_chunks_source").on(t.sourceId),
]);

export const conversations = sqliteTable("conversations", {
    id: text("id").primaryKey(),
    projectId: text("project_id").notNull().references(() => projects.id, { onDelete: "cascade" }),
    title: text("title"),
    createdAt: text("created_at").default(sql`(datetime('now'))`),
    updatedAt: text("updated_at").default(sql`(datetime('now'))`),
});

export const messages = sqliteTable("messages", {
    id: text("id").primaryKey(),
    conversationId: text("conversation_id").notNull().references(() => conversations.id, { onDelete: "cascade" }),
    role: text("role").notNull(),
    content: text("content").notNull(),
    retrievedChunks: text("retrieved_chunks"), // JSON array
    tokenCount: integer("token_count"),
    createdAt: text("created_at").default(sql`(datetime('now'))`),
}, (t) => [
    index("idx_messages_conversation").on(t.conversationId),
]);
