"""Extract demo set from Wiki dumps."""
import pickle

import typer

from utils import read_filter_terms
from extraction import wikipedia, wikidata, get_paths


def main(language: str):
    """Extracts filtered for demo purposes.
    language (str): Language to apply to Wiki extraction.
    """
    _paths = get_paths(language)
    entity_ids, entity_labels = wikidata.extract_demo_dump(
        _paths["wikidata_dump"], _paths["filtered_wikidata_dump"], read_filter_terms()
    )
    with open(_paths["filtered_entity_entity_info"], "wb") as file:
        pickle.dump((entity_ids, entity_labels), file)

    with open(_paths["filtered_entity_entity_info"], "rb") as file:
        _, entity_labels = pickle.load(file)
    wikipedia.extract_demo_dump(
        _paths["wikipedia_dump"], _paths["filtered_wikipedia_dump"], entity_labels
    )


if __name__ == "__main__":
    typer.run(main)
