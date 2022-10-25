-- DDL for parsed Wiki data.

CREATE TABLE entities (
    -- Equivalent to Wikidata QID.
    id TEXT PRIMARY KEY NOT NULL,
    -- Claims found for this entity.
    -- This could be normalized. Not worth it at the moment though, since claims aren't used.
    claims TEXT
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
    -- Wikipedia article ID (different from entity QID).
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

CREATE TABLE properties_in_entities (
    -- ID of property describing relationships between entities.
    property_id TEXT NOT NULL,
    -- ID of source entity.
    from_entity_id TEXT NOT NULL,
    -- ID of destination entity.
    to_entity_id TEXT NOT NULL,
    PRIMARY KEY (property_id, from_entity_id, to_entity_id),
    FOREIGN KEY(from_entity_id) REFERENCES entities(id),
    FOREIGN KEY(to_entity_id) REFERENCES entities(id)
);
CREATE INDEX idx_properties_in_entities
ON properties_in_entities (property_id);

CREATE TABLE aliases_for_entities (
    -- Alias for entity label.
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