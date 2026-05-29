# ---------------------------------------------------------------------------
# VLM Vector Database — stores and retrieves VLM coaching outputs
# ---------------------------------------------------------------------------

from sentence_transformers import SentenceTransformer
import numpy as np
import json
import uuid
import datetime
import os
from typing import Optional


class VLMEmbeddingModel:
    """Handles text embedding for VLM coaching feedback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True)

    def chunk_text(self, text: str, chunk_size: int = 80) -> list[str]:
        """Split text into overlapping word-level chunks to preserve context."""
        words = text.split()
        overlap = chunk_size // 4
        chunks, i = [], 0
        while i < len(words):
            chunks.append(" ".join(words[i : i + chunk_size]))
            i += chunk_size - overlap
        return chunks or [text]


class VLMVectorDatabase:
    """
    In-memory vector store for VLM coaching outputs produced by the pipeline.

    Each entry maps 1-to-1 with an AnalysisSession (via session_id) and stores
    the VLM feedback text plus the per-joint deviation scores for retrieval.

    Supports:
      - Semantic search over feedback text with optional filters
      - Score-pattern search to find similar weakness profiles
      - Player history and score aggregation
      - Save / load to JSON + numpy files
    """

    def __init__(self, embedding_model: VLMEmbeddingModel):
        self.embedding_model = embedding_model
        self.chunks: list[str] = []
        self.embeddings: list[np.ndarray] = []
        self.chunk_to_entry: list[str] = []   # chunk index → entry_id
        self.entry_ids: list[str] = []
        self.entries: dict[str, dict] = {}    # entry_id → full record
        self._indexed_session_ids: set[str] = set()

    # ------------------------------------------------------------------ #
    # Ingestion                                                            #
    # ------------------------------------------------------------------ #

    def add_vlm_output(
        self,
        vlm_feedback: str,
        scores: dict[str, float],
        session_id: Optional[str] = None,
        sport: Optional[str] = None,
        user_id: Optional[int] = None,
        shot_type: Optional[str] = None,
        video_timestamp: Optional[float] = None,
        extra_metadata: Optional[dict] = None,
    ) -> str:
        """
        Add a single VLM analysis output to the vector database.

        Args:
            vlm_feedback:    Raw coaching text from the VLM.
            scores:          Joint / motion scores, e.g.
                             {"elbow_angle": 0.82, "wrist_snap": 0.67, "overall": 0.74}
            session_id:      AnalysisSession.id this output belongs to.
            sport:           Sport type (mirrors AnalysisSession.sport_type).
            user_id:         User.id of the athlete.
            shot_type:       E.g. "smash", "serve", "backhand".
            video_timestamp: Seconds into the video.
            extra_metadata:  Any additional key-value pairs.

        Returns:
            The generated entry_id (UUID string).
        """
        entry_id = str(uuid.uuid4())

        self.entries[entry_id] = {
            "entry_id": entry_id,
            "session_id": session_id,
            "user_id": user_id,
            "sport": sport,
            "shot_type": shot_type,
            "video_timestamp": video_timestamp,
            "vlm_feedback": vlm_feedback,
            "scores": scores,
            "created_at": datetime.datetime.utcnow().isoformat(),
            **(extra_metadata or {}),
        }
        self.entry_ids.append(entry_id)
        if session_id:
            self._indexed_session_ids.add(session_id)

        chunks = self.embedding_model.chunk_text(vlm_feedback)
        embeddings = self.embedding_model.encode(chunks)
        for chunk, emb in zip(chunks, embeddings):
            self.chunks.append(chunk)
            self.embeddings.append(emb)
            self.chunk_to_entry.append(entry_id)

        return entry_id

    def add_batch(self, records: list[dict]) -> list[str]:
        """Ingest multiple VLM outputs at once. Each dict matches add_vlm_output kwargs."""
        return [self.add_vlm_output(**rec) for rec in records]

    # ------------------------------------------------------------------ #
    # Retrieval                                                            #
    # ------------------------------------------------------------------ #

    def search(
        self,
        query: str,
        k: int = 5,
        sport: Optional[str] = None,
        user_id: Optional[int] = None,
        shot_type: Optional[str] = None,
        min_overall_score: Optional[float] = None,
        max_overall_score: Optional[float] = None,
    ) -> list[dict]:
        """
        Return the top-k most semantically similar VLM outputs.

        Filters are applied before ranking; at most one result is returned
        per entry (deduplication across chunks).

        Each result dict contains:
            'entry'            — full stored record
            'matched_chunk'    — the chunk that best matched the query
            'similarity_score' — dot-product similarity
        """
        if not self.chunks:
            return []

        query_emb = self.embedding_model.encode([query])[0]
        similarities = np.dot(self.embeddings, query_emb)
        ranked_indices = np.argsort(similarities)[::-1]

        results, seen = [], set()
        for idx in ranked_indices:
            if len(results) >= k:
                break
            entry_id = self.chunk_to_entry[idx]
            if entry_id in seen:
                continue
            entry = self.entries[entry_id]

            if sport and entry.get("sport") != sport:
                continue
            if user_id is not None and entry.get("user_id") != user_id:
                continue
            if shot_type and entry.get("shot_type") != shot_type:
                continue
            overall = entry.get("scores", {}).get("overall")
            if min_overall_score is not None and (overall is None or overall < min_overall_score):
                continue
            if max_overall_score is not None and (overall is None or overall > max_overall_score):
                continue

            seen.add(entry_id)
            results.append({
                "entry": entry,
                "matched_chunk": self.chunks[idx],
                "similarity_score": float(similarities[idx]),
            })

        return results

    def search_by_score_pattern(
        self,
        scores: dict[str, float],
        k: int = 5,
        score_weight: float = 0.5,
        query: Optional[str] = None,
    ) -> list[dict]:
        """
        Find entries whose score profiles are closest to the given scores dict.

        Optionally blends cosine score-similarity with semantic text similarity
        controlled by score_weight ∈ [0, 1] (1 = scores only, 0 = text only).
        """
        all_keys = sorted({key for e in self.entries.values() for key in e["scores"]})
        if not all_keys:
            return []

        qv = np.array([scores.get(k, 0.0) for k in all_keys], dtype=float)
        qv_norm = np.linalg.norm(qv)
        if qv_norm > 0:
            qv /= qv_norm

        score_sims = {}
        for eid, entry in self.entries.items():
            vec = np.array([entry["scores"].get(k, 0.0) for k in all_keys], dtype=float)
            n = np.linalg.norm(vec)
            score_sims[eid] = float(np.dot(qv, vec / n)) if n > 0 else 0.0

        if query and self.chunks:
            qemb = self.embedding_model.encode([query])[0]
            raw = np.dot(self.embeddings, qemb)
            text_sims: dict[str, float] = {}
            for idx, eid in enumerate(self.chunk_to_entry):
                text_sims[eid] = max(text_sims.get(eid, -1.0), float(raw[idx]))
            combined = {
                eid: score_weight * score_sims.get(eid, 0.0)
                     + (1 - score_weight) * text_sims.get(eid, 0.0)
                for eid in self.entries
            }
        else:
            combined = score_sims

        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:k]
        return [{"entry": self.entries[eid], "combined_score": sim} for eid, sim in ranked]

    # ------------------------------------------------------------------ #
    # Analytics                                                            #
    # ------------------------------------------------------------------ #

    def get_user_history(
        self,
        user_id: int,
        shot_type: Optional[str] = None,
        sport: Optional[str] = None,
    ) -> list[dict]:
        """Return all entries for a user, sorted by creation date."""
        results = [
            e for e in self.entries.values()
            if e.get("user_id") == user_id
            and (shot_type is None or e.get("shot_type") == shot_type)
            and (sport is None or e.get("sport") == sport)
        ]
        return sorted(results, key=lambda x: x.get("created_at", ""))

    def aggregate_scores(
        self,
        user_id: Optional[int] = None,
        shot_type: Optional[str] = None,
        sport: Optional[str] = None,
    ) -> dict[str, float]:
        """Compute mean scores across matching entries for trend tracking."""
        pool = [
            e for e in self.entries.values()
            if (user_id is None or e.get("user_id") == user_id)
            and (shot_type is None or e.get("shot_type") == shot_type)
            and (sport is None or e.get("sport") == sport)
        ]
        if not pool:
            return {}
        all_keys: set[str] = set()
        for e in pool:
            all_keys.update(e["scores"].keys())
        return {
            key: float(np.nanmean([e["scores"].get(key, np.nan) for e in pool]))
            for key in all_keys
        }

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self, directory: str) -> None:
        """
        Persist to disk.

        Writes:
          <directory>/vlm_entries.json    — all entry records
          <directory>/vlm_chunks.json     — chunk texts + entry mapping
          <directory>/vlm_embeddings.npy  — stacked embedding matrix
        """
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vlm_entries.json"), "w") as f:
            json.dump(self.entries, f, indent=2)
        with open(os.path.join(directory, "vlm_chunks.json"), "w") as f:
            json.dump({
                "chunks": self.chunks,
                "chunk_to_entry": self.chunk_to_entry,
                "entry_ids": self.entry_ids,
            }, f)
        if self.embeddings:
            np.save(os.path.join(directory, "vlm_embeddings.npy"), np.stack(self.embeddings))

    @classmethod
    def load(cls, directory: str, embedding_model: "VLMEmbeddingModel") -> "VLMVectorDatabase":
        """
        Restore from disk.

        Usage:
            model = VLMEmbeddingModel()
            db = VLMVectorDatabase.load("./ace_vision_vectors", model)
        """
        db = cls(embedding_model)
        with open(os.path.join(directory, "vlm_entries.json")) as f:
            db.entries = json.load(f)
        with open(os.path.join(directory, "vlm_chunks.json")) as f:
            data = json.load(f)
            db.chunks = data["chunks"]
            db.chunk_to_entry = data["chunk_to_entry"]
            db.entry_ids = data["entry_ids"]
        emb_path = os.path.join(directory, "vlm_embeddings.npy")
        if os.path.exists(emb_path):
            db.embeddings = list(np.load(emb_path))
        db._indexed_session_ids = {
            e["session_id"] for e in db.entries.values() if e.get("session_id")
        }
        return db

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"VLMVectorDatabase(entries={len(self.entries)}, chunks={len(self.chunks)})"


# ── Singleton helpers ─────────────────────────────────────────────────────────

VLM_VECTOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ace_vision_vectors")

_vlm_embedding_model: Optional[VLMEmbeddingModel] = None
_vlm_vector_db: Optional[VLMVectorDatabase] = None


def get_vlm_vector_db() -> VLMVectorDatabase:
    """Return (or initialise) the process-wide VLMVectorDatabase, loading from disk on first call."""
    global _vlm_embedding_model, _vlm_vector_db
    if _vlm_vector_db is None:
        _vlm_embedding_model = VLMEmbeddingModel()
        try:
            _vlm_vector_db = VLMVectorDatabase.load(VLM_VECTOR_DIR, _vlm_embedding_model)
        except (FileNotFoundError, KeyError):
            _vlm_vector_db = VLMVectorDatabase(_vlm_embedding_model)
    return _vlm_vector_db


def save_vlm_vector_db() -> None:
    """Persist the in-memory vector DB to disk (no-op if never initialised)."""
    if _vlm_vector_db is not None:
        _vlm_vector_db.save(VLM_VECTOR_DIR)
