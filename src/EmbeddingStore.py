

from sentence_transformers import SentenceTransformer
import hnswlib
import numpy as np

# -------- Embedding/ANN store (fast + batched) --------
class EmbeddingsStore:
    """
    Maintains L2-normalized sentence embeddings + ANN (HNSW) for fast cosine checks.
    """
    def __init__(self, st_model_name="all-MiniLM-L6-v2", sim_threshold=0.85, ann_max=200_000, device=None):
        self.model_name = st_model_name
        self.model = SentenceTransformer(self.model_name, device=device)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.threshold = float(sim_threshold)

        # ANN setup
        self.ann = hnswlib.Index(space='cosine', dim=self.dim)
        self._initialized = False
        self._max_elements = int(ann_max)
        self._ef = 200
        self._M = 32
        self._next_ann_id = 0

        self.id2ann = {}      # nid -> ann_id
        self.ann2id = {}      # ann_id -> nid

    def _ensure_index(self):
        if not self._initialized:
            self.ann.init_index(max_elements=self._max_elements, ef_construction=200, M=self._M)
            self.ann.set_ef(self._ef)
            self._initialized = True

    def _maybe_grow(self, to_add: int):
        need = self._next_ann_id + to_add
        if need > self._max_elements:
            # grow in chunks to avoid frequent resizes
            new_cap = max(need + 10_000, int(self._max_elements * 1.5))
            self.ann.resize_index(new_cap)
            self._max_elements = new_cap

    def encode(self, texts, batch_size=256):
        """Return L2-normalized embeddings as float32 numpy array (N, D)."""
        if isinstance(texts, str):
            texts = [texts]
        vecs = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        vecs = np.asarray(vecs, dtype=np.float32)
        return vecs

    def max_cosine(self, vec: np.ndarray, k: int = 1) -> float:
        """Return max cosine similarity in index (or -inf if empty)."""
        if not self._initialized or self._next_ann_id == 0:
            return float("-inf")
        labels, dists = self.ann.knn_query(vec[np.newaxis, :], k=k)
        # hnswlib cosine distance = 1 - cosine_similarity
        cos = 1.0 - float(dists[0][0])
        return cos

    def is_new(self, vec: np.ndarray) -> bool:
        max_sim = self.max_cosine(vec, k=1)
        if max_sim == float("-inf"):
            return True
        return max_sim < self.threshold

    def add(self, nid: str, vec: np.ndarray):
        self._ensure_index()
        self._maybe_grow(1)
        ann_id = self._next_ann_id
        self.ann.add_items(vec[np.newaxis, :], ids=np.array([ann_id], dtype=np.int64))
        self.id2ann[nid] = ann_id
        self.ann2id[ann_id] = nid
        self._next_ann_id += 1

    def add_if_new(self, nid: str, vec: np.ndarray) -> bool:
        if self.is_new(vec):
            self.add(nid, vec)
            return True
        return False

    def batch_add_if_new(self, ids, vecs):
        """
        Vectorized(ish) path: checks each vec against ANN and adds if < threshold.
        (Queries still 1-by-1 to keep ANN logic simple.)
        Returns mask/list of bools indicating added.
        """
        added = []
        for nid, v in zip(ids, vecs):
            added.append(self.add_if_new(nid, v))
        return added
