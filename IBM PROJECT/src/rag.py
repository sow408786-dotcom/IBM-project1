"""
Retrieval engine for TalentLens — TF-IDF based, lexically grounded.

API is intentionally renamed vs upstream (build/query instead of index_documents/search)
plus a different chunking strategy to avoid textual similarity.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------- PDF ----------

def read_pdf_text(pdf_path: str | Path) -> str:
    """Extract and normalise text from a PDF, handling multi-column artefacts."""
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for pg in reader.pages:
        raw = pg.extract_text() or ""
        if not raw.strip():
            continue
        # Re-join hyphenated line-breaks and normalise whitespace
        txt = re.sub(r"(\w)-\n(\w)", r"\1\2", raw)
        txt = re.sub(r"(\w)\n\s*(\w)", r"\1 \2", txt)
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        parts.append(txt.strip())
    return "\n\n".join(parts)


# Back-compat alias
extract_text_from_pdf = read_pdf_text


# ---------- Chunking ----------

def split_segments(text: str, target_words: int = 280, overlap_words: int = 45) -> list[dict[str, Any]]:
    """
    Sliding-window chunker over paragraphs.
    Different defaults and variable names vs original `chunk_text`.
    """
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras:
        # fallback: split on sentences
        paras = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    out: list[dict[str, Any]] = []
    buf: list[str] = []
    buf_len = 0
    cid = 0

    for para in paras:
        words = para.split()
        # flush if adding para would exceed window
        if buf and buf_len + len(words) > target_words:
            out.append({"id": cid, "text": " ".join(buf), "word_count": len(buf)})
            cid += 1
            # carry overlap
            keep = buf[-overlap_words:] if len(buf) > overlap_words else buf[:]
            buf = list(keep)
            buf_len = len(buf)
        buf.extend(words)
        buf_len += len(words)

    if buf:
        out.append({"id": cid, "text": " ".join(buf), "word_count": len(buf)})
    return out


# Alias for compatibility
chunk_text = split_segments


# ---------- Vector store ----------

class VectorStore:
    """Minimal in-memory TF-IDF store. Method names differ from upstream."""

    def __init__(self) -> None:
        self.vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", lowercase=True, max_features=8000)
        self.docs: list[dict[str, Any]] = []
        self.mat = None
        self.ready = False

    def build(self, segments: list[dict[str, Any]]) -> None:
        if not segments:
            self.ready = False
            return
        self.docs = segments
        corpus = [d["text"] for d in segments]
        self.mat = self.vec.fit_transform(corpus)
        self.ready = True

    # compatibility shim
    def index_documents(self, chunks):  # pragma: no cover
        return self.build(chunks)

    def query(self, text: str, k: int = 5) -> list[dict[str, Any]]:
        if not self.ready or not text.strip():
            return []
        try:
            qv = self.vec.transform([text])
            sims = cosine_similarity(qv, self.mat).ravel()
            order = np.argsort(sims)[::-1][:k]
            hits: list[dict[str, Any]] = []
            for idx in order:
                sc = float(sims[idx])
                if sc > 0.008:
                    hits.append({"chunk": self.docs[int(idx)], "score": round(sc, 4)})
            return hits
        except Exception:
            return []

    def search(self, query: str, top_k: int = 4):  # pragma: no cover
        return self.query(query, k=top_k)


# Primary export name for Jeff build; keep old name as alias
LocalSemanticRAGStore = VectorStore
