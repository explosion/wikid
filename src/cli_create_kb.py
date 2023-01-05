"""Functionality for creating the knowledge base from downloaded assets and by querying Wikipedia's API."""
import logging
import os
from pathlib import Path

import spacy
import typer

from extraction import get_paths
from kb import WikiKB


def main(vectors_model: str, language: str):
    """Create the Knowledge Base in spaCy and write it to file.
    language (str): Language.
    vectors_model (str): Name of model with word vectors to use.
    """
    logger = logging.getLogger(__name__)
    logger.info("Constructing knowledge base.")

    output_dir = Path(os.path.abspath(__file__)).parent.parent / "output"
    nlp = spacy.load(vectors_model, enable=["tok2vec"], disable=[])
    paths = {
        "db": get_paths(language)["db"],
        "kb": output_dir / language / "kb",
        "nlp": output_dir / language / "nlp",
        "annoy": get_paths(language)["db"].parent / "wiki.annoy",
    }

    kb = WikiKB(
        nlp.vocab, nlp(".").vector.shape[0], paths["db"], paths["annoy"], language
    )

    # Build Annoy index.
    kb.build_embeddings_index(nlp)

    # Serialize knowledge base & pipeline.
    kb.to_disk(paths["kb"])
    logger.info("Successfully constructed knowledge base.")


if __name__ == "__main__":
    typer.run(main)
