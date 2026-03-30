CREATE TABLE `chunks` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`content` text NOT NULL,
	`token_count` integer NOT NULL,
	`start_element` text,
	`end_element` text,
	`heading_context` text,
	`page` integer,
	`position` integer NOT NULL,
	FOREIGN KEY (`source_id`) REFERENCES `sources`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`start_element`) REFERENCES `elements`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`end_element`) REFERENCES `elements`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `idx_chunks_source` ON `chunks` (`source_id`);--> statement-breakpoint
CREATE TABLE `conversations` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`title` text,
	`created_at` text DEFAULT (datetime('now')),
	`updated_at` text DEFAULT (datetime('now')),
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `elements` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`type` text NOT NULL,
	`level` integer,
	`content` text NOT NULL,
	`page` integer,
	`position` integer NOT NULL,
	`metadata` text,
	FOREIGN KEY (`source_id`) REFERENCES `sources`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_elements_source` ON `elements` (`source_id`);--> statement-breakpoint
CREATE TABLE `messages` (
	`id` text PRIMARY KEY NOT NULL,
	`conversation_id` text NOT NULL,
	`role` text NOT NULL,
	`content` text NOT NULL,
	`retrieved_chunks` text,
	`token_count` integer,
	`created_at` text DEFAULT (datetime('now')),
	FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_messages_conversation` ON `messages` (`conversation_id`);--> statement-breakpoint
CREATE TABLE `projects` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`description` text,
	`system_prompt` text,
	`model_id` text DEFAULT 'llama3.1:8b',
	`embedding_model` text DEFAULT 'nomic-embed-text',
	`chunk_size` integer DEFAULT 512,
	`chunk_overlap` integer DEFAULT 64,
	`top_k` integer DEFAULT 10,
	`rerank_top_n` integer DEFAULT 5,
	`created_at` text DEFAULT (datetime('now')),
	`updated_at` text DEFAULT (datetime('now'))
);
--> statement-breakpoint
CREATE TABLE `sources` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`title` text NOT NULL,
	`content_type` text NOT NULL,
	`original_path` text,
	`source_url` text,
	`language` text,
	`metadata` text,
	`status` text DEFAULT 'pending',
	`error_message` text,
	`token_count` integer,
	`chunk_count` integer,
	`created_at` text DEFAULT (datetime('now')),
	`processed_at` text,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `idx_sources_project` ON `sources` (`project_id`);