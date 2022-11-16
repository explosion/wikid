import os
import tempfile
from pathlib import Path

import pytest
import spacy

from scripts.kb import WikiKB
from scripts.extraction import establish_db_connection

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
        Path(os.path.abspath(__file__)).parent / "scripts" / "extraction" / "ddl.sql",
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
    nlp = spacy.load(
        "en_core_web_sm", exclude=["tagger", "lemmatizer", "attribute_ruler"]
    )
    kb = WikiKB(
        nlp.vocab,
        nlp(".").vector.shape[0],
        _db_path,
        _db_path.parent / "wiki.annoy",
        "en",
    )
    kb.build_embeddings_index(nlp, n_jobs=1)

    return kb


def test_kb_generation(_kb) -> None:
    """Tests KB generation."""
    print(_kb)
