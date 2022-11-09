-- DDL for parsed Wiki data.

-- Note that the four tables entities, entities_texts, articles, and article_texts could be combined into one table.
-- Two reasons why this isn't done:
--  1. For efficient full-text search we're using FTS5 virtual tables, which don't support index lookup as efficient as
--     an index lookup in a normal table. Hence we split the data we want to use for full-text search from the
--     identifiying keys (qid/article IDs).
--  2. All article data could just as well be part of the tables entities and/or entities_texts. This is not done due to
--     the sequential nature of our Wiki parsing: first the Wikidata dump (entities) are read and stored in the DB, then the
--     Wikipedia dump (articles). We could update the entities table, but this is less efficient than inserting new
--     records. If profiling shows this not to be a bottleneck, we may reconsider merging these two tables.
-- See also https://www.sqlite.org/fts5.html.

CREATE TABLE entities (
    -- Equivalent to Wikidata QID.
    id TEXT PRIMARY KEY NOT NULL
);

-- The FTS5 virtual table implementation doesn't allow for indices, so we rely on ROWID to match entities.
-- This isn't great, but with a controlled data ingestion setup this allows for stable matching.
-- Same for foreign keys.
CREATE VIRTUAL TABLE entities_texts USING fts5(
    -- Equivalent to Wikidata QID. UNINDEXED signifies that this field is not indexed for full text search.
    entity_id UNINDEXED,
    -- Entity name.
    name,
    -- Entity description.
    description,
    -- Entity label.
    label
);

CREATE TABLE articles (
    -- Equivalent to Wikdata QID.
    entity_id TEXT PRIMARY KEY NOT NULL,
    -- Wikipedia article ID (different from qid QID).
    id TEXT NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);
CREATE UNIQUE INDEX idx_articles_id
ON articles (id);

-- Same here: no indices possible, relying on ROWID to match with articles.
CREATE VIRTUAL TABLE articles_texts USING fts5(
    -- Equivalent to Wikidata QID. UNINDEXED signifies that this field is not indexed for full text search.
    entity_id UNINDEXED,
    -- Article title.
    title,
    -- Article text.
    content
);

-- Virtual table for aliases, capable of on-disk fuzzy matching.
-- https://sqlite.org/spellfix1.html
-- This duplicates aliases also in aliases_for_entities. A better long-term solution would be to reference aliases in
-- this table via their ROWID, but requires more involved ways to insert and query data to ensure data integrity (the
-- spellfix table can't have additional indices, just like FTS5).
CREATE VIRTUAL TABLE aliases USING spellfix1;

CREATE TABLE aliases_for_entities (
    -- Alias' row ID for entity label.
    alias TEXT NOT NULL,
    -- Equivalent to Wikidata QID.
    entity_id TEXT NOT NULL,
    -- Count of alias occurence in Wiki articles.
    count INTEGER,
    PRIMARY KEY (alias, entity_id),
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);
CREATE INDEX idx_aliases_for_entities_alias
ON aliases_for_entities (alias);
CREATE INDEX idx_aliases_for_entities_entity_id
ON aliases_for_entities (entity_id);