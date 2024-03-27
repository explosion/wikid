""" Wiki dataset for unified access to information from Wikipedia and Wikidata dumps. """
import os.path
import pickle
from pathlib import Path
from typing import Dict, Any, Tuple, List, Set, Optional

from .compat import sqlite3
from . import schemas
from . import wikidata
from . import wikipedia


def _get_paths(language: str) -> Dict[str, Path]:
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
    db_path = _get_paths(language)["db"]
    os.makedirs(db_path.parent, exist_ok=True)
    db_conn = sqlite3.connect(_get_paths(language)["db"])
    db_conn.row_factory = sqlite3.Row
    return db_conn


def extract_demo_dump(filter_terms: Set[str], language: str) -> None:
    """Extracts small demo dump by parsing the Wiki dumps and keeping only those entities (and their articles)
    containing any of the specified filter_terms. The retained entities and articles are written into intermediate
    files.
    filter_terms (Set[str]): Terms having to appear in entity descriptions in order to be wrr
    language (str): Language.
    """

    _paths = _get_paths(language)
    entity_ids, entity_labels = wikidata.extract_demo_dump(
        _paths["wikidata_dump"], _paths["filtered_wikidata_dump"], filter_terms
    )
    with open(_paths["filtered_entity_entity_info"], "wb") as file:
        pickle.dump((entity_ids, entity_labels), file)

    with open(_paths["filtered_entity_entity_info"], "rb") as file:
        _, entity_labels = pickle.load(file)
    wikipedia.extract_demo_dump(
        _paths["wikipedia_dump"], _paths["filtered_wikipedia_dump"], entity_labels
    )


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

    _paths = _get_paths(language)
    msg = "Database exists already. Execute `weasel run delete_db` to remove it."
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
    """Loads information for entity or entities by querying information from DB.
    Note that this doesn't return all available information, only the part used in the current benchmark solution.
    language (str): Language.
    qids (Tuple[str]): QIDS to look up. If empty, all entities are loaded.
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
            """
            % ",".join("?" * len(qids)),
            tuple(set(qids)),
        )
    }


def load_alias_entity_prior_probabilities(
    language: str, db_conn: Optional[sqlite3.Connection] = None
) -> Dict[str, List[Tuple[str, float]]]:
    """Loads alias-entity counts from database and transforms them into prior probabilities per alias.
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
