"""Functionality for creating the knowledge base from downloaded assets and by querying Wikipedia's API."""
# import logging

# import spacy
#
# from extraction import get_paths
# from kb import WikiKB


def main(vectors_model: str, language: str):
    """Create the Knowledge Base in spaCy and write it to file.
    language (str): Language.
    vectors_model (str): Name of model with word vectors to use.
    """

    # u = AnnoyIndex(300, 'dot')
    # u.load("/home/raphael/dev/wikid/output/en/wiki.annoy")
    # print(u.get_nns_by_item(1, 50))
    # exit()

    # logger = logging.getLogger(__name__)
    # nlp = spacy.load(vectors_model, exclude=["tagger", "lemmatizer", "attribute_ruler"])
    #
    # wkb = WikiKB(
    #     nlp.vocab,
    #     get_paths(language)["db"],
    #     get_paths(language)["db"].parent / "wiki.annoy",
    #     language,
    # )
    # doc = nlp(
    #     "Barack Obama is the 44th president of the United States. He was born in Hawaii. He is the first black "
    #     "president of the US."
    # )
    # mentions1 = [doc[0:2], doc[4:6], doc[4:10], doc[8:10], doc[-2]]
    # doc = nlp(
    #     "The New York Knicks played the Boston Celtics today. New York beat Boston by 12 points."
    # )
    # mentions2 = [doc[1:4], doc[6:8], doc[10:12], doc[13:14]]
    # print(mentions2)
    # # wkb.get_candidates_all([mentions1])
    # wkb.get_candidates_all([mentions2])

    # logger.info("Constructing knowledge base.")
    # kb = KnowledgeBase(vocab=nlp.vocab, entity_vector_length=nlp.vocab.vectors_length)
    # entity_list: List[str] = []
    # count_list: List[int] = []
    # vector_list: List[numpy.ndarray] = []  # type: ignore
    # entities = load_entities(language=language)
    #
    # # Infer vectors for entities' descriptions.
    # desc_vectors = [
    #     doc.vector
    #     for doc in tqdm.tqdm(
    #         nlp.pipe(
    #             texts=[
    #                 entities[qid].name
    #                 + " "
    #                 + (" ".join(entities[qid].aliases) if entities[qid].aliases else "")
    #                 + " "
    #                 + (
    #                     entities[qid].description
    #                     if entities[qid].description
    #                     else (
    #                         entities[qid].article_text[:500]
    #                         if entities[qid].article_text
    #                         else entities[qid].name
    #                     )
    #                 )
    #                 for qid in entities.keys()
    #             ],
    #             n_process=-1,
    #         ),
    #         total=len(entities),
    #         desc="Inferring entity embeddings",
    #     )
    # ]
    # for qid, desc_vector in zip(entities.keys(), desc_vectors):
    #     entity_list.append(qid)
    #     count_list.append(entities[qid].count)
    #     vector_list.append(
    #         desc_vector if isinstance(desc_vector, numpy.ndarray) else desc_vector.get()
    #     )
    # kb.set_entities(
    #     entity_list=entity_list, vector_list=vector_list, freq_list=count_list
    # )
    #
    # # Add aliases with normalized priors to KB. This won't be necessary with a custom KB.
    # alias_entity_prior_probs = load_alias_entity_prior_probabilities(language=language)
    # for alias, entity_prior_probs in alias_entity_prior_probs.items():
    #     kb.add_alias(
    #         alias=alias,
    #         entities=[epp[0] for epp in entity_prior_probs],
    #         probabilities=[epp[1] for epp in entity_prior_probs],
    #     )
    # # Add pseudo aliases for easier lookup with new candidate generators.
    # for entity_id in entity_list:
    #     kb.add_alias(
    #         alias="_" + entity_id + "_", entities=[entity_id], probabilities=[1]
    #     )
    #
    # # Serialize knowledge base & pipeline.
    # output_dir = Path(os.path.abspath(__file__)).parent.parent / "output"
    # kb.to_disk(output_dir / language / "kb")
    # nlp_dir = output_dir / language / "nlp"
    # os.makedirs(nlp_dir, exist_ok=True)
    # nlp.to_disk(nlp_dir)
    # logger.info("Successfully constructed knowledge base.")


if __name__ == "__main__":
    # typer.run(main)
    main("en_core_web_lg", "en")
