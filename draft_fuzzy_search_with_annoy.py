import annoy
import tqdm

from scripts.extraction import establish_db_connection


if __name__ == "__main__":
    language = "en"
    terminal_symbol = "<END>"
    db_conn = establish_db_connection(language)
    # Cap max_alias_length - some aliases are longer, but even for those matching the first k chars should be
    # sufficient.
    max_alias_length = min(
        db_conn.cursor()
        .execute("SELECT max(length(alias)) AS max_length FROM aliases_for_entities")
        .fetchone()["max_length"],
        30,
    )
    max_row_id = (
        db_conn.cursor()
        .execute("SELECT count(*) FROM aliases_for_entities")
        .fetchone()["count(*)"]
    )
    #
    aliases = [
        dict(row)
        for row in db_conn.cursor()
        .execute(
            f"""
            SELECT
                substr(afe.alias, 1, {max_alias_length}) as alias_short,
                min(afe.ROWID) as rowid
            FROM
                aliases_for_entities afe
            GROUP BY
                alias,
                substr(alias, 1, 50)
            """
        )
        .fetchall()
    ]

    max_alias_length += len(terminal_symbol)  # + len(str(max_row_id))
    _annoy = annoy.AnnoyIndex(max_alias_length, "angular")
    _annoy.on_disk_build("/tmp/alias.annoy")
    for i, alias in enumerate(tqdm.tqdm(aliases, desc="Converting aliases")):
        vector = alias["alias_short"] + terminal_symbol  # + str(alias["rowid"])
        unicode_repr = [
            ord(char) for char in vector.ljust(max_alias_length, " ")[:max_alias_length]
        ]
        _annoy.add_item(i, unicode_repr)
    print("building")
    _annoy.build(n_trees=10, n_jobs=-1)
    _annoy = annoy.AnnoyIndex(max_alias_length, "angular")
    _annoy.load("/tmp/alias.annoy")

    tst = "Barack"
    tst = [ord(char) for char in (tst + terminal_symbol).ljust(max_alias_length, " ")][
        :max_alias_length
    ]

    for i in _annoy.get_nns_by_vector(tst, 50):
        vector = _annoy.get_item_vector(i)
        result_converted = "".join([chr(int(v)) for v in vector])
        print(result_converted)
