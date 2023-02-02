import os
import tempfile
from pathlib import Path
from typing import List

import pytest
import spacy
import srsly
from spacy.tokens import Span

from src.kb import WikiKB
from src.extraction import establish_db_connection

_language = "en"


@pytest.fixture
def _db_path() -> Path:
    """Generates test DB.
    RETURNS (Path): Path to database in temporary directory.
    """
    tmp_dir = Path(tempfile.TemporaryDirectory().name)
    db_path = tmp_dir / "wiki.sqlite"

    # Construct DB.
    db_conn = establish_db_connection(_language, db_path)
    with open(
        Path(os.path.abspath(__file__)).parent / "src" / "extraction" / "ddl.sql",
        "r",
    ) as ddl_sql:
        db_conn.cursor().executescript(ddl_sql.read())

    # Fill DB.
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO entities (id) VALUES ('Q60'), ('Q100'), ('Q597');")
    cursor.execute(
        """
        INSERT INTO entities_texts (entity_id, name, description, label) VALUES
            ('Q60', 'New York City', 'most populous city in the United States', 'New York City'),
            ('Q100', 'Boston', 'capital and largest city of Massachusetts, United States', 'Boston'),
            ('Q597', 'Lisbon', 'capital city of Portugal', 'Lisbon');
        """
    )
    cursor.execute(
        "INSERT INTO articles (entity_id, id) VALUES (60, 0), (100, 1), (597, 2);"
    )
    cursor.execute(
        """
        INSERT INTO articles_texts (entity_id, title, content) VALUES
            (
                'Q60',
                'New York City',
                'New York, often called New York City (NYC), is the most populous city in the United States. With a
                2020 population of 8,804,190 distributed over 300.46 square miles (778.2 km2), New York City is also the
                most densely populated major city in the United States. The city is within the southern tip of New York
                State, and constitutes the geographical and demographic center of both the Northeast megalopolis and the
                New York metropolitan area – the largest metropolitan area in the world by urban landmass.'
            ),
            (
                'Q100',
                'Boston',
                'Boston (US: /ˈbɔːstən/), officially the City of Boston, is the state capital and most populous city of
                the Commonwealth of Massachusetts, as well as the cultural and financial center of the New England
                region of the United States. It is the 24th-most populous city in the country. The city boundaries
                encompass an area of about 48.4 sq mi (125 km2) and a population of 675,647 as of 2020.'
            ),
            (
                'Q597',
                'Lisbon',
                'Lisbon (/ˈlɪzbən/; Portuguese: Lisboa [liʒˈboɐ] (listen)) is the capital and the largest city of
                Portugal, with an estimated population of 544,851 within its administrative limits in an area of
                100.05 km2. Lisbon''s urban area extends beyond the city''s administrative limits with a population of
                around 2.7 million people, being the 11th-most populous urban area in the European Union. About 3
                million people live in the Lisbon metropolitan area, making it the third largest metropolitan area in
                the Iberian Peninsula, after Madrid and Barcelona.'
            )
        ;
        """
    )
    cursor.execute(
        """
        INSERT INTO aliases_for_entities (alias, entity_id, count, prior_prob) VALUES
            ('NYC', 'Q60', 1, 0.01),
            ('New York', 'Q60', 1, 0.01),
            ('the five boroughs', 'Q60', 1, 0.01),
            ('Big Apple', 'Q60', 1, 0.01),
            ('City of New York', 'Q60', 1, 0.01),
            ('NY City', 'Q60', 1, 0.01),
            ('New York, New York', 'Q60', 1, 0.01),
            ('New York City, New York', 'Q60', 1, 0.01),
            ('New York, NY', 'Q60', 1, 0.01),
            ('New York City (NYC)', 'Q60', 1, 0.01),
            ('New York (city)', 'Q60', 1, 0.01),
            ('New York City, NY', 'Q60', 1, 0.01),
            ('Caput Mundi', 'Q60', 1, 0.01),
            ('The City So Nice They Named It Twice', 'Q60', 1, 0.01),
            ('Capital of the World', 'Q60', 1, 0.01),

            ('Boston', 'Q100', 1, 0.01),
            ('Beantown', 'Q100', 1, 0.01),
            ('The Cradle of Liberty', 'Q100', 1, 0.01),
            ('The Hub', 'Q100', 1, 0.01),
            ('The Cradle of Modern America', 'Q100', 1, 0.01),
            ('The Athens of America', 'Q100', 1, 0.01),
            ('The Walking City', 'Q100', 1, 0.01),
            ('The Hub of the Universe', 'Q100', 1, 0.01),
            ('Bostonia', 'Q100', 1, 0.01),
            ('Boston, Massachusetts', 'Q100', 1, 0.01),
            ('Boston, Mass.', 'Q100', 1, 0.01),
            ('Puritan City', 'Q100', 1, 0.01),

            ('Lisbon', 'Q597', 1, 0.01),
            ('Lisboa', 'Q597', 1, 0.01);
        """
    )
    cursor.execute(
        "INSERT INTO aliases (word) SELECT distinct(alias) FROM aliases_for_entities;"
    )
    db_conn.commit()
    return db_path


@pytest.fixture
def _kb(_db_path) -> WikiKB:
    """Generates KB.
    _db_path (Path): Path to database / fixture constructing database in temporary directory.
    RETURNS (WikiKB): WikiKB instance.
    """
    nlp = spacy.load("en_core_web_sm")
    kb = WikiKB(
        nlp.vocab,
        nlp(".").vector.shape[0],
        _db_path,
        _db_path.parent / "wiki.annoy",
        "en",
    )
    kb.build_embeddings_index(nlp, n_jobs=1)

    return kb


@pytest.fixture
def _kb_with_lookup_file(_kb, _db_path) -> WikiKB:
    """
    Generates WikiKB using a lookup file.
    _kb (WikiKB): KB without lookup file, used to generated lookup file.
    _db_path (_db_path): Path to generated database.
    RETURNS (WikiKB): WikiKB using a lookup file.
    """
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("new yorc and Boston")
    mentions = [doc[:2], doc[3:]]
    cands = list(next(_kb.get_candidates_all([mentions])))
    lookup_path = _db_path.parent / "mention_lookups.json"

    srsly.write_json(
        lookup_path,
        {
            mention.text: [cand.asdict() for cand in cands[i]]
            for i, mention in enumerate(mentions)
        },
    )

    kb = WikiKB(
        _kb.vocab,
        _kb.entity_vector_length,
        _db_path,
        _db_path.parent / "wiki.annoy",
        "en",
        mentions_candidates_path=lookup_path,
    )
    # Skip embeddings index generation since it already exists (via fixture _kb).

    return kb


def test_initialization(_kb) -> None:
    """Tests KB intialization."""
    # Check DB content.
    assert all(
        [
            _kb._db_conn.cursor()
            .execute(f"SELECT count(*) FROM {table}")
            .fetchone()["count(*)"]
            == 3
            for table in ("entities", "articles", "entities_texts", "articles_texts")
        ]
    )
    assert len(_kb) == 3
    assert (
        _kb._db_conn.cursor()
        .execute("SELECT count(*) FROM aliases_for_entities")
        .fetchone()["count(*)"]
        == 29
    )
    assert (
        _kb._db_conn.cursor()
        .execute("SELECT count(*) FROM aliases")
        .fetchone()["count(*)"]
        == 29
    )

    # Check Annoy index.
    assert len(_kb._annoy.get_item_vector(0)) == _kb.entity_vector_length
    assert _kb._annoy.get_n_items() == 3


@pytest.mark.parametrize("method", ["bytes", "disk"])
def test_serialization(_kb, method: str) -> None:
    """Tests KB serialization (to and from byte strings, to and from disk).
    method (str): Method to use for serialization. Has to be one of ("bytes", "disk").
    """
    assert method in ("bytes", "disk")
    nlp = spacy.load(
        "en_core_web_sm", exclude=["tagger", "lemmatizer", "attribute_ruler"]
    )

    # Create KB for comparison with diverging values.
    kb = WikiKB(
        nlp.vocab,
        nlp(".").vector.shape[0] + 1,
        _kb._paths["db"],
        Path("this_path_doesnt_exist"),
        "es",
        n_trees=100,
        top_k_aliases=100,
        top_k_entities_alias=100,
        top_k_entities_fts=100,
        threshold_alias=1000,
    )

    # Reset KB to serialized reference KB.
    if method == "bytes":
        kb.from_bytes(_kb.to_bytes())
    else:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            kb_file_path = Path(tmp_dir_name) / "kb"
            _kb.to_disk(kb_file_path)
            kb.from_disk(kb_file_path)

    assert _verify_kb_equality(_kb, kb)


def test_factory_method(_kb) -> None:
    """Tests factory method to generate WikiKB instance from file."""
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        kb_file_path = Path(tmp_dir_name) / "kb"
        _kb.to_disk(kb_file_path)
        kb = WikiKB.generate_from_disk(kb_file_path)

    assert _verify_kb_equality(_kb, kb)


def _verify_kb_equality(kb1: WikiKB, kb2: WikiKB) -> bool:
    """Checks whether kb1 and kb2 have identical values for all arguments (doesn't check on DB equality).
    kb1 (WikiKB): First instance.
    kb2 (WikiKB): Second instance.
    RETURNS (bool): Whether kb1 and kb2 have identical values for all arguments.
    """
    return all(
        [
            getattr(kb1, attr_name) == getattr(kb2, attr_name)
            for attr_name in (
                "_paths",
                "_language",
                "_n_trees",
                "entity_vector_length",
                "_hashes",
                "_top_k_aliases",
                "_top_k_entities_alias",
                "_top_k_entities_fts",
                "_threshold_alias",
            )
        ]
    )


def _verify_candidate_retrieval_results(
    kb: WikiKB, mentions: List[Span], target_entity_ids: List[List[str]]
):
    """Assert that retrieved candidates are correct.
    kb (WikiKB): KB to use.
    mentions (List[Span]): Mentions to resolve.
    target_entity_ids (List[List[str]]): Expected target entity IDs per mention.
    """

    for i, (cands_from_all, cands_from_single) in enumerate(
        zip(
            next(kb.get_candidates_all([mentions])),
            [kb.get_candidates(mention) for mention in mentions],
        )
    ):
        assert len(list(cands_from_all)) == len(list(cands_from_single))
        for j, (cand_all, cand_single) in enumerate(
            zip(cands_from_all, cands_from_single)
        ):
            assert cand_all.entity == target_entity_ids[i][j]
            # Check for equality between candidates generated by get_candidates_all() and those generated by
            # get_candidates().
            for prop in ("entity", "entity_", "entity_vector", "mention", "prior_prob"):
                assert getattr(cand_all, prop) == getattr(cand_single, prop)


def test_get_candidates(_kb) -> None:
    """Smoke test for get_candidates() and get_candidates_all()."""
    doc = spacy.load("en_core_web_sm")("new yorc and Boston")
    _verify_candidate_retrieval_results(
        _kb, [doc[:2], doc[3:]], [["Q60"], ["Q100", "Q60"]]
    )


def test_serialized_mention_lookups(_kb_with_lookup_file) -> None:
    """Tests serialized mention lookups."""
    # Monkeypatch candidate search methods to make sure we don't use them.
    def _raise(_) -> None:
        raise Exception

    _kb_with_lookup_file._fetch_candidates_by_alias = _raise

    # Test lookup works correctly.
    doc = spacy.load("en_core_web_sm")("new yorc and Boston")
    _verify_candidate_retrieval_results(
        _kb_with_lookup_file, [doc[:2], doc[3:]], [["Q60"], ["Q100", "Q60"]]
    )
