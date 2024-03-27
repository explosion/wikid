""" Parsing of Wiki dump and persisting of parsing results to DB. """
from typing import Optional
import typer
from wiki import parse


def main(
    language: str,
    # Argument instead of option so it can be overwritten by other spaCy projects (otherwise escaping makes it
    # impossible to pass on '--OPTION', since it's interpreted as dedicated option ("--vars.OPTION --OPTION") instead
    # of as "--vars.OPTION '--OPTION'", as it should be.
    use_filtered_dumps: bool,
    entity_limit: Optional[int] = typer.Option(None, "--entity_limit"),
    article_limit: Optional[int] = typer.Option(None, "--article_limit"),
    alias_limit: Optional[int] = typer.Option(None, "--alias_limit"),
):
    """Parses Wikidata and Wikipedia dumps. Persists parsing results to DB. If one of the _limit variables is reached,
    parsing is stopped.
    language (str): Language (e.g. 'en', 'es', ...) to assume for Wiki dump.
    use_filtered_dumps (bool): Whether to use filtered Wiki dumps instead of the full ones.
    entity_limit (Optional[int]): Max. number of entities to parse. Unlimited if None.
    article_limit (Optional[int]): Max. number of articles to parse. Unlimited if None.
    alias_limit (Optional[int]): Max. number of entity aliases to parse. Unlimited if None.
    """

    parse(
        language=language,
        use_filtered_dumps=use_filtered_dumps,
        entity_config={"limit": entity_limit},
        article_text_config={"limit": article_limit},
        alias_prior_prob_config={"limit": alias_limit},
    )


if __name__ == "__main__":
    typer.run(main)
