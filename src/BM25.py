from typing import Dict, List, Tuple, Iterable, Union, Optional
from rank_bm25 import BM25Okapi
import re
import nltk
from nltk.corpus import stopwords

class BM25NeedsIndex:
    def __init__(self, needs: Optional[Dict[str, str]] = None):
        """
        needs: optional initial mapping {need_id: need_text}
        """
        self._tokenize = lambda s: re.findall(r"\w+", s.lower())
        self.needs: Dict[str, str] = dict(needs) if needs else {}
        self._ids: List[str] = []
        self._docs_tok: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        nltk.download("stopwords", quiet=True)
        self.stopwords= set(stopwords.words("english"))
        self._rebuild()

    def _preprocess(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = self._tokenize(text)
        tokens = [t for t in text if t and t not in self.stopwords]
        return tokens

    # ---------- public API ----------
    def add_need(self, need_id: str, need_text: str, overwrite: bool = False) -> None:
        if (need_id in self.needs) and not overwrite:
            raise ValueError(f"need_id '{need_id}' already exists. Set overwrite=True to replace.")
        self.needs[need_id] = need_text
        # Incremental add (rebuild keeps things simple & correct for small/med corpora)
        self._rebuild()

    def add_needs(self, items: Union[Dict[str, str], Iterable[Tuple[str, str]]], overwrite: bool = False) -> None:
        if isinstance(items, dict):
            items = items.items()
        for nid, txt in items:
            if (nid in self.needs) and not overwrite:
                raise ValueError(f"need_id '{nid}' already exists. Set overwrite=True to replace.")
            self.needs[nid] = txt
        self._rebuild()

    def update_need(self, need_id: str, new_text: str) -> None:
        if need_id not in self.needs:
            raise KeyError(f"need_id '{need_id}' not found.")
        self.needs[need_id] = new_text
        self._rebuild()

    def remove_need(self, need_id: str) -> None:
        if need_id in self.needs:
            del self.needs[need_id]
            self._rebuild()

    def clear(self) -> None:
        """Clear all needs from the index."""
        self.needs.clear()
        self._rebuild()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Union[str, float]]]:
        """Return top_k needs most similar to query as [{id, need, score}, ...]."""
        if not self._bm25 or not self._ids:
            return []
        qtok = self._preprocess(query)
        scores = self._bm25.get_scores(qtok)
        # stable sort by (-score, id) for deterministic ties
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], self._ids[i]))
        out = []
        for i in ranked[:top_k]:
            nid = self._ids[i]
            if float(scores[i]) > 0:
                out.append({"id": nid, "description": self.needs[nid], "score": float(scores[i])})
        return out

    # ---------- internals ----------
    def _rebuild(self) -> None:
        self._ids = list(self.needs.keys())
        self._docs_tok = [self._preprocess(self.needs[nid]) for nid in self._ids]
        self._bm25 = BM25Okapi(self._docs_tok) if self._docs_tok else None
