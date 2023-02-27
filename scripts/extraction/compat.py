# Import pysqlite3, if available. This allows for more flexibility in downstream applications/deployments, as the SQLITE
# version coupled to the Python version might not support all the features needed for `wikid` to work (e. g. FTS5
# virtual tables). Fall back to bundled sqlite3 otherwise.
try:
    import pysqlite3 as sqlite3
except ModuleNotFoundError:
    import sqlite3

__all__ = ["sqlite3"]
