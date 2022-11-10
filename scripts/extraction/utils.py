import os.path
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import sqlite3

import sqlite_spellfix

from . import schemas
from . import wikidata
from . import wikipedia


def get_paths(language: str) -> Dict[str, Path]:
    """Get paths.
    language (str): Language.
    RETURNS (Dict[str, Path]): Paths.
    """

    _root_dir = Path(os.path.abspath(__file__)).parent.parent.parent
    _assets_dir = _root_dir / "assets"
    return {
        "db": _root_dir / "output" / language / "wiki.sqlite3",
        "wikidata_dump": _assets_dir / "wikidata_entity_dump.json.bz2",
        "wikipedia_dump": _assets_dir / f"{language}-wikipedia_dump.xml.bz2",
        "filtered_wikidata_dump": _assets_dir
        / "wikidata_entity_dump_filtered.json.bz2",
        "filtered_wikipedia_dump": _assets_dir / "wikipedia_dump_filtered.xml.bz2",
    }


def establish_db_connection(language: str) -> sqlite3.Connection:
    """Estabished database connection.
    language (str): Language.
    RETURNS (sqlite3.Connection): Database connection.
    """
    db_path = get_paths(language)["db"]
    os.makedirs(db_path.parent, exist_ok=True)
    db_conn = sqlite3.connect(get_paths(language)["db"])

    # Use row factory to obtain records as dicts.
    db_conn.row_factory = sqlite3.Row
    # Enable spellfix1 for fuzzy search (https://sqlite.org/spellfix1.html).
    db_conn.enable_load_extension(True)
    db_conn.load_extension(sqlite_spellfix.extension_path())

    return db_conn


def parse(
    language: str,
    db_conn: Optional[sqlite3.Connection] = None,
    entity_config: Optional[Dict[str, Any]] = None,
    article_text_config: Optional[Dict[str, Any]] = None,
    alias_prior_prob_config: Optional[Dict[str, Any]] = None,
    use_filtered_dumps: bool = False,
) -> None:
    """Parses Wikipedia and Wikidata dumps. Writes parsing results to a database. Note that this takes hours.
    language (str): Language (e.g. 'en', 'es', ...) to assume for Wiki dump.
    db_conn (Optional[sqlite3.Connection]): Database connection.
    entity_config (Dict[str, Any]): Arguments to be passed on to wikidata.read_entities().
    article_text_config (Dict[str, Any]): Arguments to be passed on to wikipedia.read_text().
    alias_prior_prob_config (Dict[str, Any]): Arguments to be passed on to wikipedia.read_prior_probs().
    use_filtered_dumps (bool): Whether to use small, filtered Wiki dumps.
    """

    _paths = get_paths(language)
    msg = "Database exists already. Execute `spacy project run delete_wiki_db` to remove it."
    assert not os.path.exists(_paths["db"]), msg

    db_conn = db_conn if db_conn else establish_db_connection(language)
    with open(Path(os.path.abspath(__file__)).parent / "ddl.sql", "r") as ddl_sql:
        db_conn.cursor().executescript(ddl_sql.read())

    wikidata.read_entities(
        _paths["wikidata_dump"]
        if not use_filtered_dumps
        else _paths["filtered_wikidata_dump"],
        db_conn,
        **(entity_config if entity_config else {}),
        lang=language,
        parse_properties=False,
        parse_claims=False,
    )

    wikipedia.read_prior_probs(
        _paths["wikipedia_dump"]
        if not use_filtered_dumps
        else _paths["filtered_wikipedia_dump"],
        db_conn,
        **(alias_prior_prob_config if alias_prior_prob_config else {}),
    )

    wikipedia.read_texts(
        _paths["wikipedia_dump"]
        if not use_filtered_dumps
        else _paths["filtered_wikipedia_dump"],
        db_conn,
        **(article_text_config if article_text_config else {}),
    )


def load_entities(
    language: str,
    qids: Tuple[str, ...] = tuple(),
    db_conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, schemas.Entity]:
    """Loads information for entities by querying information from DB.
    Note that this doesn't return all available information, only the part used in the current benchmark solution.
    language (str): Language.
    qids (Tuple[str]): QIDS to look up. If empty, all qids are loaded.
    db_conn (Optional[sqlite3.Connection]): Database connection.
    RETURNS (Dict[str, Entity]): Information on requested entities.
    """
    db_conn = db_conn if db_conn else establish_db_connection(language)

    return {
        rec["id"]: schemas.Entity(
            qid=rec["id"],
            name=rec["entity_title"],
            aliases={
                alias
                for alias in {
                    rec["entity_title"],
                    rec["article_title"],
                    rec["label"],
                    *(rec["aliases"] if rec["aliases"] else "").split(","),
                }
                if alias
            },
            article_title=rec["article_title"],
            article_text=rec["content"],
            description=rec["description"],
            count=rec["count"] if rec["count"] else 0,
        )
        for rec in db_conn.cursor().execute(
            f"""
                SELECT
                    e.id,
                    et.name as entity_title,
                    et.description,
                    et.label,
                    at.title as article_title,
                    at.content,
                    GROUP_CONCAT(afe.alias) as aliases,
                    SUM(afe.count) as count
                FROM
                    entities e
                LEFT JOIN entities_texts et on
                    et.ROWID = e.ROWID
                LEFT JOIN articles a on
                    a.entity_id = e.id
                LEFT JOIN articles_texts at on
                    at.ROWID = a.ROWID
                LEFT JOIN aliases_for_entities afe on
                    afe.entity_id = e.id
                WHERE
                    {'FALSE' if len(qids) else 'TRUE'} OR e.id IN (%s)
                GROUP BY
                    e.id,
                    et.name,
                    et.description,
                    et.label,
                    at.title,
                    at.content
                ORDER BY
                    e.rowid
            """
            % ",".join("?" * len(qids)),
            tuple(set(qids)),
        )
    }


def load_alias_entity_prior_probabilities(
    language: str, db_conn: Optional[sqlite3.Connection] = None
) -> Dict[str, List[Tuple[str, float]]]:
    """Loads alias-qid counts from database and transforms them into prior probabilities per alias.
    language (str): Language.
    RETURN (Dict[str, Tuple[Tuple[str, ...], Tuple[float, ...]]]): Mapping of alias to tuples of entities and the
        corresponding prior probabilities.
    """

    db_conn = db_conn if db_conn else establish_db_connection(language)

    alias_entity_prior_probs = {
        rec["alias"]: [
            (entity_id, int(count))
            for entity_id, count in zip(
                rec["entity_ids"].split(","), rec["counts"].split(",")
            )
        ]
        for rec in db_conn.cursor().execute(
            """
                SELECT
                    alias,
                    GROUP_CONCAT(entity_id) as entity_ids,
                    GROUP_CONCAT(count) as counts
                FROM
                    aliases_for_entities
                GROUP BY
                    alias
            """
        )
    }

    for alias, entity_counts in alias_entity_prior_probs.items():
        total_count = sum([ec[1] for ec in entity_counts])
        alias_entity_prior_probs[alias] = [
            (ec[0], ec[1] / max(total_count, 1)) for ec in entity_counts
        ]

    return alias_entity_prior_probs
