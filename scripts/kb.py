import hashlib
import logging
import os.path
import pickle

from itertools import chain
from pathlib import Path
from typing import Iterable, Iterator, Tuple, Union, Optional, Dict, Any, List, Sized

import annoy
import numpy
import spacy
import srsly
import tqdm
from spacy import Vocab, Language
from spacy.kb import KnowledgeBase, Candidate
from spacy.tokens import Span
from spacy.util import SimpleFrozenList

from extraction.utils import (
    establish_db_connection,
    load_entities,
)


class WikiKB(KnowledgeBase):
    """Knowledge base handling storage and access to Wikidata/Wikipedia data."""

    def __init__(
        self,
        vocab: Vocab,
        entity_vector_length: int,
        db_path: Path,
        annoy_path: Path,
        language: str,
        n_trees: int = 50,
        top_k_aliases: int = 5,
        top_k_entities_alias: int = 20,
        top_k_entities_fts: int = 5,
        threshold_alias: int = 100,
    ):
        """Initializes from existing SQLite database generated by `wikid`.
        Loads Annoy index file (as mmap) into memory, if file exists at specified path.
        vocab (Vocab): Pipeline vocabulary.
        entity_vector_length (int): Length of entity vectors.
        db_path (Path): Path to SQLite database.
        annoy_path (Path): Path to Annoy index file.
        language (str): Language.
        n_trees (int): Number of trees in Annoy index. Precision in NN queries correspond with number of trees. Ignored
            if Annoy index file already exists.
        top_k_aliases (int): Top k aliases matches to consider. An alias may be associated with more than one entity, so
            this parameter does _not_ necessarily correspond to the the maximum number of identified candidates. For
            that use top_k_alias_entity.
        top_k_alias_entity (int): Top k entities to consider in list of alias matches. Equals maximum number of
            candidate entities found via alias search.
        top_k_entities_fts (int): Top k of full-text search matches to consider. Equals maximum number of candidate entities
            found via full-text search.
        threshold_alias (int): Threshold for alias distance as calculated by spellfix1.
        """
        super().__init__(vocab, entity_vector_length)

        self._paths = {"db": db_path, "annoy": annoy_path}
        self._language = language
        self._annoy: Optional[annoy.AnnoyIndex] = None
        self._n_trees = n_trees
        self._db_conn = establish_db_connection(language, self._paths["db"])
        self._embedding_dim = self.entity_vector_length
        self._hashes: Dict[str, Optional[str]] = {}
        self._top_k_aliases = top_k_aliases
        self._top_k_entities_alias = top_k_entities_alias
        self._top_k_entities_fts = top_k_entities_fts
        self._threshold_alias = threshold_alias

        if os.path.exists(self._paths["annoy"]):
            self._init_annoy_from_file()

    def build_embeddings_index(self, nlp: Language, n_jobs: int = -1) -> None:
        """Constructs index for embeddings with Annoy and stores them in an index file.
        nlp (Language): Pipeline with tok2vec for inferring embeddings.
        n_jobs (int): Number of jobs to use for inferring entity embeddings and building the index.
        """

        logger = logging.getLogger(__name__)

        # Initialize ANN index.
        self._annoy = annoy.AnnoyIndex(self._embedding_dim, "angular")
        self._annoy.on_disk_build(str(self._paths["annoy"]))
        batch_size = 100000

        row_count = (
            self._db_conn.cursor()
            .execute("SELECT count(*) FROM entities")
            .fetchone()["count(*)"]
        )

        # Build Annoy index in batches.
        for row_id in tqdm.tqdm(
            # We select by ROWID, which starts at 1.
            range(1, row_count + 1, batch_size),
            desc="Inferring entity embeddings",
            position=0,
        ):
            ids = tuple(
                (row["id"], row["ROWID"])
                for row in self._db_conn.cursor()
                .execute(
                    f"""
                        SELECT
                            id,
                            ROWID
                        FROM
                            entities
                        WHERE
                            ROWID BETWEEN {row_id} AND {row_id + batch_size - 1}
                        ORDER BY
                            ROWID
                        """
                )
                .fetchall()
            )
            qids = tuple(_id[0] for _id in ids)
            entities = load_entities(
                language=self._language, qids=qids, db_conn=self._db_conn
            )

            # Assemble descriptions to be embedded.
            ent_descs = [
                " ".join({entities[qid].name, *entities[qid].aliases})
                + " "
                + (
                    entities[qid].description
                    if entities[qid].description
                    else (
                        entities[qid].article_text[:500]
                        if entities[qid].article_text
                        else ""
                    )
                )
                for qid in qids
            ]

            for row_id_offset, qid, desc_vector in zip(
                range(len(qids)),
                qids,
                [
                    ent_desc_doc.vector
                    for ent_desc_doc in nlp.pipe(texts=ent_descs, n_process=n_jobs)
                ],
            ):
                self._annoy.add_item(
                    # Annoy expects index to start with 0, so we index each entities vector by its entities.ROWID value
                    # in the database shifted by -1.
                    row_id + row_id_offset - 1,
                    desc_vector
                    if isinstance(desc_vector, numpy.ndarray)
                    else desc_vector.get(),
                )

        logger.info("Building ANN index.")
        self._annoy.build(n_trees=self._n_trees, n_jobs=n_jobs)

    def get_candidates_all(
        self, mentions: Iterator[Iterable[Span]]
    ) -> Iterator[Iterable[Iterable[Candidate]]]:
        """
        Retrieve candidate entities for specified mentions per document. If no candidate is found for a given mention,
        an empty list is returned.
        mentions (Iterator[Iterable[Span]]): Mentions per documents for which to get candidates.
        YIELDS (Iterator[Iterable[Iterable[Candidate]]]): Identified candidates per document.
        """
        for mentions_in_doc in mentions:
            mentions_in_doc = tuple(mentions_in_doc)
            alias_matches = self._fetch_candidates_by_alias(mentions_in_doc)
            fts_matches = self._fetch_candidates_by_fts(mentions_in_doc)
            # Candidates for each mention per document.
            candidates: List[List[Candidate]] = []

            for i, mention in enumerate(mentions_in_doc):
                candidates.append([])

                for cand_data in alias_matches.get(mention.text, []):
                    candidates[i].append(
                        Candidate(
                            kb=self,
                            entity_freq=cand_data["sum_occurence_count"],
                            prior_prob=cand_data["max_prior_prob"],
                            entity_vector=next(
                                iter(self._get_vectors([cand_data["rowid"]]))
                            ),
                            # Hashes aren't used by WikiKB.
                            entity_hash=0,
                            alias_hash=0,
                        )
                    )

                for cand_data in fts_matches.get(mention.text, []):
                    candidates[i].append(
                        Candidate(
                            kb=self,
                            entity_freq=cand_data["sum_occurence_count"],
                            prior_prob=-1,
                            entity_vector=next(
                                iter(self._get_vectors([cand_data["rowid"]]))
                            ),
                            # Hashes aren't used by WikiKB.
                            entity_hash=0,
                            alias_hash=0,
                        )
                    )

            yield candidates

    def get_candidates(self, mention: Span) -> Iterable[Candidate]:
        """
        Retrieve candidate entities for specified mention. If no candidate is found for a given mention, an empty list
        is returned.
        mention (Span): Mention for which to get candidates.
        RETURNS (Iterable[Candidate]): Identified candidates.
        """
        return next(iter(next(self.get_candidates_all([mention]))))

    def _get_vectors(self, rowids: Iterable[int]) -> Iterable[Iterable[float]]:
        """
        Return vectors for entities.
        rowids (Iterable[int]): ROWID values for entities in table `entities`.
        RETURNS (Iterable[Iterable[float]]): Vectors for specified entities.
        """
        # Annoy doesn't seem to offer batched retrieval.
        return [self._annoy.get_item_vector(rowid - 1) for rowid in rowids]

    def get_vectors(self, qids: Iterable[str]) -> Iterable[Iterable[float]]:
        """
        Return vectors for entities.
        qids (str): Wiki QIDs.
        RETURNS (Iterable[Iterable[float]]): Vectors for specified entities.
        """
        if not isinstance(qids, Sized):
            qids = set(qids)

        # Fetch row IDs for QIDs, resolve to vectors in Annoy index.
        return self._get_vectors(
            [
                row["ROWID"]
                for row in self._db_conn.cursor()
                .execute(
                    "SELECT ROWID FROM entities WHERE id in (%s)"
                    % ",".join("?" * len(qids)),
                    tuple(qids),
                )
                .fetchall()
            ]
        )

    def get_vector(self, qid: str) -> Iterable[float]:
        """
        Return vector for qid.
        qid (str): Wiki QID.
        RETURNS (Iterable[float]): Vector for specified entities.
        """
        return next(iter(self.get_vectors([qid])))

    @staticmethod
    def _hash_file(file_path: Path, blocksize: int = 2**20) -> str:
        """Generates MD5 file of hash iteratively (without loading entire file into memory).
        Source: https://stackoverflow.com/a/1131255.
        file_path (Path): Path of file to hash.
        blocksize (int): Size of blocks to load into memory (in bytes).
        RETURN (str): MD5 hash of file.
        """
        file_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            buf = f.read(blocksize)
            while buf:
                file_hash.update(buf)
                buf = f.read(blocksize)
        return file_hash.hexdigest()

    def _fetch_candidates_by_alias(
        self, mentions: Tuple[Span, ...]
    ) -> Dict[str, List[Dict[str, Union[str, int, float]]]]:
        """Fetches candidates for mentions by fuzzily matching aliases to the mentions.
        mentions (Tuple[Span, ..]): List of mentions for which to fetch candidates.
        RETURN List[Dict[str, Dict[str, Union[str, int, float]]]]: List of candidates per mention, sorted by distance
            to mention, (3) occurence count in Wikipedia.
        """
        # Subquery to fetch alias values for single mention.
        mention_subquery = f"""
            SELECT alias, 0 as distance, null as score FROM aliases_for_entities WHERE alias = ?
            UNION
            SELECT word, distance, score FROM aliases WHERE word MATCH ? AND distance <= {self._threshold_alias}
        """

        grouped_rows: Dict[str, List[Dict[str, Union[str, int, float]]]] = {}
        for row in [
            dict(row)
            for row in self._db_conn.execute(
                """
                SELECT
                    matches.mention,
                    matches.entity_id,
                    matches.max_prior_prob,
                    matches.sum_occurence_count,
                    matches.min_distance,
                    e.ROWID
                FROM ("""
                + "\nUNION ALL\n".join(
                    [
                        f"""
                            SELECT
                                *
                            FROM (
                                SELECT
                                    matches.mention,
                                    ae.entity_id,
                                    max(ae.prior_prob) as max_prior_prob,
                                    sum(ae.count) as sum_occurence_count,
                                    min(matches.distance) as min_distance
                                FROM (
                                    SELECT
                                        ? as mention,
                                        matches.alias,
                                        matches.distance
                                    FROM
                                        ({mention_subquery}) matches
                                    ORDER BY
                                        score
                                    LIMIT {self._top_k_aliases}
                                ) matches
                                INNER JOIN aliases_for_entities ae on
                                    ae.alias = matches.alias
                                GROUP BY
                                    ae.entity_id
                                ORDER BY
                                    min_distance,
                                    sum_occurence_count DESC
                                LIMIT {self._top_k_entities_alias}
                            )
                        """
                    ]
                    * len(mentions)
                )
                + f"""
                ) matches
                INNER JOIN entities e ON
                    e.id = matches.entity_id
                ORDER BY
                    matches.mention
                """,
                list(
                    chain.from_iterable(
                        [mention.text, mention.text, mention.text]
                        for mention in mentions
                    )
                ),
            ).fetchall()
        ]:
            mention = row.pop("mention")
            grouped_rows[mention] = [*grouped_rows.get(mention, []), row]

        return grouped_rows

    def _fetch_candidates_by_fts(
        self, mentions: Tuple[Span, ...]
    ) -> Dict[str, List[Dict[str, Union[str, int, float]]]]:
        """Fetches candidates for mentions by searching in Wikidata entity descriptions.
        mentions (Tuple[Span, ...]): List of mentions for which to fetch candidates.
        RETURN (Dict[str, List[Dict[str, Union[str, int, float]]]]): Lists of candidiates per mention, sorted by (1)
            mention and (2) BM25 score.
        """
        # Subquery to fetch alias values for single mentions.
        query = ""
        for i, mention in enumerate(mentions):
            query += f"""
                SELECT
                    '{mention.text}' as mention,
                    match.score,
                    match.entity_id,
                    match.rowid,
                    sum(afe.count) as sum_occurence_count
                FROM (
                    SELECT
                        bm25(entities_texts) as score,
                        et.entity_id,
                        et.ROWID as rowid
                    FROM
                        entities_texts et
                    WHERE
                        entities_texts MATCH '{mention.text}'
                    ORDER BY
                        bm25(entities_texts)
                    LIMIT {self._top_k_entities_fts}
                ) match
                INNER JOIN entities e ON
                    e.ROWID = match.ROWID
                INNER JOIN aliases_for_entities afe ON
                    e.id = afe.entity_id
                GROUP BY
                    mention,
                    match.score,
                    match.entity_id,
                    match.rowid
            """
            if i < len(mentions) - 1:
                query += "\nUNION ALL\n"

        grouped_rows: Dict[str, List[Dict[str, Union[str, int, float]]]] = {}
        for row in [dict(row) for row in self._db_conn.execute(query).fetchall()]:
            mention = row.pop("mention")
            grouped_rows[mention] = [*grouped_rows.get(mention, []), row]

        return grouped_rows

    def _init_annoy_from_file(self) -> None:
        """Inits Annoy index."""
        self._annoy = annoy.AnnoyIndex(self._embedding_dim, "angular")
        self._annoy.load(str(self._paths["annoy"]))

    def _update_hash(self, key: str) -> str:
        """Updates hash.
        key (str): Key for file to hash - has to be in self._paths.
        RETURNS (str): File hash.
        """
        self._hashes[key] = self._hash_file(self._paths[key])
        return self._hashes[key]

    def to_bytes(self, **kwargs) -> bytes:
        """Serialize the current state to a binary string.
        RETURNS (bytes): Current state as binary string.
        """
        return spacy.util.to_bytes(
            {
                "meta": lambda: srsly.json_dumps(
                    data=(
                        self._language,
                        {key: str(path) for key, path in self._paths.items()},
                        self._embedding_dim,
                        self._top_k_aliases,
                        self._top_k_entities_fts,
                        self._threshold_alias,
                        self._update_hash("db"),
                        self._update_hash("annoy"),
                    )
                ).encode("utf-8"),
                "vocab": self.vocab.to_bytes,
            },
            [],
        )

    def from_bytes(
        self, bytes_data: bytes, *, exclude: Tuple[str] = tuple()
    ) -> "WikiKB":
        """Load state from a binary string.
        bytes_data (bytes): KB state.
        exclude (Tuple[str]): Properties to exclude when restoring KB.
        """

        def deserialize_meta(value: bytes) -> None:
            """De-serialize meta info.
            value (bytes): Byte string to deserialize.
            """
            meta_info = srsly.json_loads(value)
            self._language = meta_info[0]
            self._paths = {k: Path(v) for k, v in meta_info[1].items()}
            self._embedding_dim = meta_info[2]
            self._top_k_aliases = meta_info[3]
            self._top_k_entities_fts = meta_info[4]
            self._threshold_alias = meta_info[5]
            self._hashes["db"] = meta_info[7]
            self._hashes["annoy"] = meta_info[8]

            self._init_annoy_from_file()
            for file_id in ("annoy", "db"):
                assert self._hashes[file_id] == self._hash_file(
                    self._paths[file_id]
                ), f"File with internal ID {file_id} does not match deserialized hash."

        def deserialize_vocab(value: bytes):
            """De-serialize vocab.
            value (bytes): Byte string to deserialize.
            """
            self.vocab.from_bytes(value)

        spacy.util.from_bytes(
            bytes_data, {"meta": deserialize_meta, "vocab": deserialize_vocab}, exclude
        )

        return self

    def to_disk(
        self, path: Union[str, Path], exclude: Iterable[str] = SimpleFrozenList()
    ) -> None:
        """
        Write WikiKnowledgeBase content to disk.
        path (Union[str, Path]): Target file path.
        exclude (Iterable[str]): List of components to exclude.
        """
        path = spacy.util.ensure_path(path)
        if not path.exists():
            path.mkdir(parents=True)
        if not path.is_dir():
            raise ValueError(spacy.Errors.E928.format(loc=path))

        def pickle_data(value: Any, file_path: Path) -> None:
            """
            Pickles info to disk.
            value (Any): Value to pickle.
            file_path (Path): File path.
            """
            with open(file_path, "wb") as file:
                pickle.dump(value, file)

        self._update_hash("db")
        self._update_hash("annoy")

        serialize = {
            "meta": lambda p: pickle_data(
                (
                    self._language,
                    self._paths,
                    self._embedding_dim,
                    self._top_k_aliases,
                    self._top_k_entities_fts,
                    self._threshold_alias,
                    self._hashes,
                ),
                p,
            ),
            "vocab.json": lambda p: self.vocab.strings.to_disk(p),
        }
        spacy.util.to_disk(path, serialize, exclude)

    def from_disk(
        self, path: Union[str, Path], exclude: Iterable[str] = SimpleFrozenList()
    ) -> None:
        """
        Load WikiKnowledgeBase content from disk.
        path (Union[str, Path]): Target file path.
        exclude (Iterable[str]): List of components to exclude.
        """
        path = spacy.util.ensure_path(path)
        if not path.exists():
            raise ValueError(spacy.Errors.E929.format(loc=path))
        if not path.is_dir():
            raise ValueError(spacy.Errors.E928.format(loc=path))

        def deserialize_meta_info(file_path: Path) -> None:
            """
            Deserializes meta info.
            file_path (Path): File path.
            RETURNS (Any): Deserializes meta info.
            """
            with open(file_path, "rb") as file:
                meta_info = pickle.load(file)
                self._language = meta_info[0]
                self._paths = meta_info[1]
                self._embedding_dim = meta_info[2]
                self._top_k_aliases = meta_info[3]
                self._top_k_entities_fts = meta_info[4]
                self._threshold_alias = meta_info[5]
                self._hashes = meta_info[7]

                self._init_annoy_from_file()
                for file_id in ("annoy", "db"):
                    assert self._hashes[file_id] == self._hash_file(
                        self._paths[file_id]
                    ), f"File with internal ID {file_id} does not match deserialized hash."

        deserialize = {
            "meta": lambda p: deserialize_meta_info(p),
            "vocab.json": lambda p: self.vocab.strings.from_disk(p),
        }
        spacy.util.from_disk(path, deserialize, exclude)

    @staticmethod
    def _pick_candidate_sequences(
        embeddings: numpy.ndarray, beam_width: int
    ) -> List[Tuple[List[int], float]]:
        """Pick sequences of candidates, ranked by their cohesion. Cohesion is measured as the average cosine similarity
        between the average embedding in a sequence and the individual embeddings.
        Each row contains all candidates per mention. Selects heuristically via beam search.
        Modified from https://machinelearningmastery.com/beam-search-decoder-natural-language-processing/.
        embeddings (numpy.ndarray): 2D matrix with embedding vectors per candidate.
        beam_width (int): Beam width.
        RETURN (List[Tuple[List[int], float]]): List of sequences of candidate indices in embeddings matrix & their
            corresponding cohesion score.
        """
        # todo add shape check (3D) for embeddings
        # todo step-by-step debugging with real data to verify assumptions
        # todo ensure correct shape processing in numpy operations
        sequences: List[Tuple[List[int], float]] = [([], 0.0)]
        dim = len(embeddings[0][0])

        for row_idx, row in enumerate(embeddings):
            all_candidates: List[Tuple[List[int], float]] = []
            # Expand each candidate.
            for i in range(len(sequences)):
                sequence = sequences[i]
                # Compute sum of embeddings already in this sequence. If this is the first row and `sequences` is hence
                # empty, we assume a vector of zeroes.
                seq_prev_embeddings = [
                    embeddings[_row_idx][col_idx]
                    for _row_idx, col_idx in enumerate(sequence[0])
                ]
                seq_sum_prev_embeddings = (
                    numpy.sum(seq_prev_embeddings) if row_idx > 0 else numpy.zeros(dim)
                )

                for j in range(len(row)):
                    # Compute average sequence embedding, including potential next sequence element.
                    seq_avg_embedding = numpy.sum(seq_sum_prev_embeddings, row[j]) / (
                        row_idx + 1
                    )
                    seq_embeddings = [*seq_prev_embeddings, row[j]]

                    # Compute cohesion as cosine similarity.
                    cohesion = numpy.mean(
                        (seq_avg_embedding @ seq_embeddings)
                        / (
                            numpy.linalg.norm(seq_avg_embedding)
                            * numpy.linalg.norm(seq_embeddings)
                        )
                    )
                    candidate = [(*sequence[0], j), cohesion]
                    all_candidates.append(candidate)

            # Order all candidates by cohesion, select beam_width best sets.
            sequences = sorted(all_candidates, key=lambda tup: tup[1])[:beam_width]  # type: ignore

        return sequences
