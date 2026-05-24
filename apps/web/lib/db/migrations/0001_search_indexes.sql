CREATE VIRTUAL TABLE IF NOT EXISTS `chunk_embeddings` USING vec0(
	`chunk_id` text PRIMARY KEY,
	`embedding` float[2560]
);
--> statement-breakpoint
CREATE VIRTUAL TABLE IF NOT EXISTS `chunk_fts` USING fts5(
	`chunk_id` UNINDEXED,
	`source_id` UNINDEXED,
	`source_title`,
	`content`,
	`heading_context`,
	tokenize = 'unicode61 remove_diacritics 2'
);
--> statement-breakpoint
CREATE TRIGGER IF NOT EXISTS `chunks_ai_fts`
AFTER INSERT ON `chunks`
BEGIN
	INSERT INTO chunk_fts (`chunk_id`, `source_id`, `source_title`, `content`, `heading_context`)
	SELECT
		NEW.id,
		NEW.source_id,
		COALESCE(s.title, ''),
		NEW.content,
		COALESCE(NEW.heading_context, '')
	FROM `sources` AS s
	WHERE s.id = NEW.source_id;
END;
--> statement-breakpoint
CREATE TRIGGER IF NOT EXISTS `chunks_ad_fts`
AFTER DELETE ON `chunks`
BEGIN
	DELETE FROM chunk_fts WHERE chunk_id = OLD.id;
END;
--> statement-breakpoint
CREATE TRIGGER IF NOT EXISTS `chunks_au_fts`
AFTER UPDATE ON `chunks`
BEGIN
	DELETE FROM chunk_fts WHERE chunk_id = OLD.id;
	INSERT INTO chunk_fts (`chunk_id`, `source_id`, `source_title`, `content`, `heading_context`)
	SELECT
		NEW.id,
		NEW.source_id,
		COALESCE(s.title, ''),
		NEW.content,
		COALESCE(NEW.heading_context, '')
	FROM `sources` AS s
	WHERE s.id = NEW.source_id;
END;
--> statement-breakpoint
CREATE TRIGGER IF NOT EXISTS `sources_au_chunk_fts`
AFTER UPDATE OF `title` ON `sources`
BEGIN
	DELETE FROM chunk_fts WHERE source_id = NEW.id;
	INSERT INTO chunk_fts (`chunk_id`, `source_id`, `source_title`, `content`, `heading_context`)
	SELECT
		c.id,
		c.source_id,
		COALESCE(NEW.title, ''),
		c.content,
		COALESCE(c.heading_context, '')
	FROM `chunks` AS c
	WHERE c.source_id = NEW.id;
END;
--> statement-breakpoint
INSERT INTO chunk_fts (`chunk_id`, `source_id`, `source_title`, `content`, `heading_context`)
SELECT
	c.id,
	c.source_id,
	COALESCE(s.title, ''),
	c.content,
	COALESCE(c.heading_context, '')
FROM `chunks` AS c
INNER JOIN `sources` AS s ON s.id = c.source_id
WHERE NOT EXISTS (
	SELECT 1
	FROM chunk_fts AS f
	WHERE f.chunk_id = c.id
);
