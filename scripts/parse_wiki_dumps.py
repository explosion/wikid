""" Parsing of Wiki dump and persisting of parsing results to DB. """
from typing import Optional
import typer
from wiki import wiki_dump_api


def main(
    language: str,
    entity_limit: Optional[int] = typer.Option(None, "--entity_limit"),
    article_limit: Optional[int] = typer.Option(None, "--article_limit"),
    alias_limit: Optional[int] = typer.Option(None, "--alias_limit"),
    use_filtered_dumps: bool = typer.Option(False, "--filter"),
):
    """Parses Wikidata and Wikipedia dumps. Persists parsing results to DB. If one of the _limit variables is reached,
    parsing is stopped.
    language (str): Language (e.g. 'en', 'es', ...) to assume for Wiki dump.
    entity_limit (Optional[int]): Max. number of entities to parse. Unlimited if None.
    article_limit (Optional[int]): Max. number of entities to parse. Unlimited if None.
    alias_limit (Optional[int]): Max. number of entity aliases to parse. Unlimited if None.
    use_filtered_dumps (bool): Whether to use filtered Wiki dumps instead of the full ones.
    """

    wiki_dump_api.parse(
        language=language,
        entity_config={"limit": entity_limit},
        article_text_config={"limit": article_limit},
        alias_prior_prob_config={"limit": alias_limit},
        use_filtered_dumps=use_filtered_dumps,
    )


if __name__ == "__main__":
    typer.run(main)
