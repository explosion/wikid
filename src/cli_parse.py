""" Parsing of Wiki dump and persisting of parsing results to DB. """
from typing import Optional
import typer

from extraction import parse


def main(
    language: str,
    # Argument instead of option so it can be overwritten by other spaCy projects (otherwise escaping makes it
    # impossible to pass on '--OPTION', since it's interpreted as dedicated option ("--vars.OPTION --OPTION") instead
    # of as "--vars.OPTION '--OPTION'", as it should be.
    use_filtered_dumps: bool,
    merge_with_en_aliases: bool = typer.Option(True, "--merge_with_en_aliases"),
    store_meta_entities: bool = typer.Option(False, "--store_meta_entitities"),
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
    alias_limit (Optional[int]): Max. number of qid aliases to parse. Unlimited if None.
    merge_with_en_aliases (bool): Whether to merge aliases in Wikidata in target language with English aliases. If the
        target language is English, this doesn't have any effect.
    store_meta_entities (bool): Whether to store meta entities (disambiguations, categories, ...) in database/knowledge
        base.
    """

    parse(
        language=language,
        use_filtered_dumps=use_filtered_dumps,
        entity_config={"limit": entity_limit},
        article_text_config={"limit": article_limit},
        alias_prior_prob_config={"limit": alias_limit},
        merge_with_en_aliases=merge_with_en_aliases,
        store_meta_entities=store_meta_entities,
    )


if __name__ == "__main__":
    typer.run(main)
