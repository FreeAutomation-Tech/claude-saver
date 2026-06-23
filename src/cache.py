import sqlite3
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np

CACHE_DIR = Path.home() / ".claude-saver"
CACHE_DB = CACHE_DIR / "cache.db"
SIMILARITY_THRESHOLD = 0.92


def _ensure_db():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            prompt_hash TEXT PRIMARY KEY,
            prompt_text TEXT,
            response_text TEXT,
            model TEXT,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hit_count INTEGER DEFAULT 1,
            tokens_saved INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embeddings_cache (
            text_hash TEXT PRIMARY KEY,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_embedding(text: str):
    from sentence_transformers import SentenceTransformer
    conn = _ensure_db()
    text_h = _text_hash(text)
    row = conn.execute(
        "SELECT embedding FROM embeddings_cache WHERE text_hash = ?",
        (text_h,)
    ).fetchone()
    if row:
        return np.frombuffer(row[0], dtype=np.float32)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(text, normalize_embeddings=True)
    conn.execute(
        "INSERT OR REPLACE INTO embeddings_cache (text_hash, embedding) VALUES (?, ?)",
        (text_h, emb.astype(np.float32).tobytes())
    )
    conn.commit()
    return emb


def _cosine_similarity(a, b):
    return float(np.dot(a, b))


def get_cached_response(
    prompt: str, model: str, threshold: float = SIMILARITY_THRESHOLD
) -> Optional[str]:
    conn = _ensure_db()
    prompt_emb = _get_embedding(prompt)
    rows = conn.execute(
        "SELECT prompt_hash, prompt_text, response_text, embedding FROM responses WHERE model = ?",
        (model,)
    ).fetchall()
    best_match = None
    best_score = 0.0
    for ph, pt, rt, emb_bytes in rows:
        if emb_bytes:
            cached_emb = np.frombuffer(emb_bytes, dtype=np.float32)
            score = _cosine_similarity(prompt_emb, cached_emb)
            if score > best_score:
                best_score = score
                best_match = (ph, rt, score)
    if best_match and best_score >= threshold:
        ph, rt, _ = best_match
        conn.execute(
            "UPDATE responses SET hit_count = hit_count + 1 WHERE prompt_hash = ?",
            (ph,)
        )
        conn.commit()
        return rt
    return None


def cache_response(prompt: str, response: str, model: str, tokens_saved: int = 0):
    conn = _ensure_db()
    prompt_h = _text_hash(prompt)
    emb = _get_embedding(prompt)
    conn.execute(
        """INSERT OR REPLACE INTO responses
           (prompt_hash, prompt_text, response_text, model, embedding, tokens_saved)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (prompt_h, prompt, response, model, emb.astype(np.float32).tobytes(), tokens_saved)
    )
    conn.commit()


def get_cache_stats() -> dict:
    conn = _ensure_db()
    total = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    total_hits = conn.execute("SELECT SUM(hit_count) FROM responses").fetchone()[0] or 0
    total_tokens = conn.execute("SELECT SUM(tokens_saved) FROM responses").fetchone()[0] or 0
    total_tokens = int(total_tokens)
    newest = conn.execute(
        "SELECT created_at FROM responses ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    oldest = conn.execute(
        "SELECT created_at FROM responses ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    return {
        "total_cached": total,
        "total_hits": int(total_hits),
        "total_tokens_saved": total_tokens,
        "newest_entry": newest[0] if newest else None,
        "oldest_entry": oldest[0] if oldest else None,
    }


def clear_cache():
    conn = _ensure_db()
    conn.execute("DELETE FROM responses")
    conn.execute("DELETE FROM embeddings_cache")
    conn.commit()
