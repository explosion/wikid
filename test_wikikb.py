import os
import tempfile
from pathlib import Path

from extraction import establish_db_connection

_language = "en"


def _generate_test_db() -> Path:
    """Generates test DB.
    RETURNS (Path): Path to database in temporary directory.
    """
    tmp_dir = tempfile.TemporaryDirectory().name
    db_path = tmp_dir / "wiki.sqlite"

    # Construct DB.
    db_conn = establish_db_connection(_language)
    with open(Path(os.path.abspath(__file__)).parent / "ddl.sql", "r") as ddl_sql:
        db_conn.cursor().executescript(ddl_sql.read())

    # Fill DB.
    cursor = db_conn.cursor()
    cursor.execute(
        """
        -- New York, Boston, Lisbon.
        INSERT INTO entities (id) VALUES (60);
        INSERT INTO entities (id) VALUES (100);
        INSERT INTO entities (id) VALUES (597);

        INSERT INTO entities_texts (entity_id, name, description, label)
        VALUES (
            60,
            'New York City',
            'most populous city in the United States',
            'New York City'
        );
        INSERT INTO entities_texts (entity_id, name, description, label)
        VALUES (
            100,
            'Boston',
            'capital and largest city of Massachusetts, United States',
            'Boston'
        );
        INSERT INTO entities_texts (entity_id, name, description, label)
        VALUES (
            597,
            'Lisbon',
            'capital city of Portugal',
            'Lisbon'
        );
        """
    )

    return db_path
