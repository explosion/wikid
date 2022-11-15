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

    return db_path
