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

    nlp = spacy.load(vectors_model, exclude=["tagger", "lemmatizer", "attribute_ruler"])
    kb = WikiKB(
        nlp.vocab,
        nlp(".").vector.shape[0],
        get_paths(language)["db"],
        get_paths(language)["db"].parent / "wiki.annoy",
        language,
    )
    # doc = nlp(
    #     "Barack Obama is the 44th president of the United States. He was born in Hawaii. He is the first black "
    #     "president of the US."
    # )
    # mentions1 = [doc[0:2], doc[4:6], doc[4:10], doc[8:10], doc[-2]]
    # doc = nlp(
    #     "The New York Knicks played the Boston Celtics today. New York beat Boston by 12 points."
    # )
    # mentions2 = [doc[1:4], doc[6:8], doc[10:12], doc[13:14]]
    # cands = list(wkb.get_candidates_all([mentions1, mentions2]))
    # x = 3

    # Build Annoy index.
    kb.build_embeddings_index(nlp)

    # Serialize knowledge base & pipeline.
    output_dir = Path(os.path.abspath(__file__)).parent.parent / "output"
    kb.to_disk(output_dir / language / "kb")
    nlp_dir = output_dir / language / "nlp"
    os.makedirs(nlp_dir, exist_ok=True)
    nlp.to_disk(nlp_dir)
    logger.info("Successfully constructed knowledge base.")


if __name__ == "__main__":
    typer.run(main)
