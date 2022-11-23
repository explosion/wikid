import spacy

if __name__ == "__main__":
    nlp = spacy.load("en_coreference_web_trf")

    examples = [
        "The Boston Celtics played against the New York Knicks today. Boston beat New York by 5 points.",
        "Patrick Ewing went to Boston. He didn't like it there very much.",
        "The Boston Celtics played against the New York Knicks today. The game took place in Boston.",
        "Barack Obama was the 44th President. The president was in Rome today. Obama held a speech. His first name is Barack.",
        "Natalie Portman won an Oscar. Portman starred in many movies.",
        "Natalie Portman won an Oscar. Nat starred in many movies.",
        "Natalie Portman won an Oscar. Nicolas Cage starred in many movies.",
        "Natalie Portman won an Oscar. Cage starred in many movies.",
        "Natalie Portman won an Oscar. Nic starred in many movies.",
        "Explosion develops spaCy and prodi.gy. The company is located in Berlin.",
        "Explosion develops spaCy and prodi.gy. Berlin is the company's location.",
    ]

    for ex in examples:
        doc = nlp(ex)
        print(doc)
        print("=== word clusters ===")
        word_clusters = [
            val for key, val in doc.spans.items() if key.startswith("coref_head")
        ]
        for cluster in word_clusters:
            print(cluster)
        # check the expanded clusters
        print("=== full clusters ===")
        full_clusters = [
            val for key, val in doc.spans.items() if key.startswith("coref_cluster")
        ]
        for cluster in full_clusters:
            print(cluster)
        print("---------------------------")
