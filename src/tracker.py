import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_DIR = Path.home() / ".claude-saver"
DB_PATH = DB_DIR / "usage.db"

CLAUDE_MODEL_COSTS = {
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-2.1": {"input": 8.0, "output": 24.0},
    "claude-2.0": {"input": 8.0, "output": 24.0},
    "claude-instant-1.2": {"input": 0.8, "output": 2.4},
}

DEFAULT_COST = {"input": 3.0, "output": 15.0}

COST_PER_1K_TOKENS = {
    "claude-3-opus-20240229": 0.075,
    "claude-3-sonnet-20240229": 0.015,
    "claude-3-haiku-20240307": 0.0025,
}

CACHE_COST_PER_1K = 0.0025


def _ensure_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cached_tokens INTEGER DEFAULT 0,
            cost REAL,
            saved REAL DEFAULT 0.0,
            prompt_preview TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_totals (
            date TEXT PRIMARY KEY,
            total_cost REAL DEFAULT 0.0,
            total_saved REAL DEFAULT 0.0,
            total_prompt_tokens INTEGER DEFAULT 0,
            total_completion_tokens INTEGER DEFAULT 0,
            total_cached_tokens INTEGER DEFAULT 0,
            request_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def get_model_cost(model: str) -> dict:
    return CLAUDE_MODEL_COSTS.get(model, DEFAULT_COST)


def log_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int = 0,
    prompt_preview: str = "",
):
    conn = _ensure_db()
    costs = get_model_cost(model)
    input_cost = (prompt_tokens / 1000) * costs["input"]
    output_cost = (completion_tokens / 1000) * costs["output"]
    total_cost = input_cost + output_cost

    saved = (cached_tokens / 1000) * costs["input"]

    conn.execute(
        """INSERT INTO usage_log
           (model, prompt_tokens, completion_tokens, cached_tokens, cost, saved, prompt_preview)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (model, prompt_tokens, completion_tokens, cached_tokens,
         round(total_cost, 6), round(saved, 6), prompt_preview[:100])
    )

    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("""
        INSERT INTO daily_totals (date, total_cost, total_saved, total_prompt_tokens,
                                  total_completion_tokens, total_cached_tokens, request_count)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(date) DO UPDATE SET
            total_cost = total_cost + ?,
            total_saved = total_saved + ?,
            total_prompt_tokens = total_prompt_tokens + ?,
            total_completion_tokens = total_completion_tokens + ?,
            total_cached_tokens = total_cached_tokens + ?,
            request_count = request_count + 1
    """, (
        today,
        round(total_cost, 6), round(saved, 6), prompt_tokens, completion_tokens, cached_tokens,
        round(total_cost, 6), round(saved, 6), prompt_tokens, completion_tokens, cached_tokens,
    ))
    conn.commit()


def get_usage_stats(days: int = 30) -> dict:
    conn = _ensure_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    row = conn.execute("""
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(cost), 0) as total_cost,
            COALESCE(SUM(saved), 0) as total_saved,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
            COALESCE(SUM(cached_tokens), 0) as total_cached_tokens
        FROM usage_log
        WHERE timestamp >= ?
    """, (cutoff,)).fetchone()

    daily = conn.execute("""
        SELECT date, total_cost, total_saved, total_cached_tokens, request_count
        FROM daily_totals
        WHERE date >= ?
        ORDER BY date DESC
    """, (cutoff,)).fetchall()

    model_breakdown = conn.execute("""
        SELECT model,
               COUNT(*) as count,
               COALESCE(SUM(cost), 0) as model_cost,
               COALESCE(SUM(saved), 0) as model_saved
        FROM usage_log
        WHERE timestamp >= ?
        GROUP BY model
        ORDER BY model_cost DESC
    """, (cutoff,)).fetchall()

    savings_rate = 0
    total_spend = float(row[1]) + float(row[2])
    if total_spend > 0:
        savings_rate = (float(row[2]) / total_spend) * 100

    return {
        "period_days": days,
        "total_requests": row[0],
        "total_cost": round(float(row[1]), 4),
        "total_saved": round(float(row[2]), 4),
        "total_prompt_tokens": row[3],
        "total_completion_tokens": row[4],
        "total_cached_tokens": row[5],
        "savings_rate": round(savings_rate, 1),
        "daily": [
            {"date": d[0], "cost": round(float(d[1]), 4),
             "saved": round(float(d[2]), 4), "cached": d[3], "requests": d[4]}
            for d in daily
        ],
        "model_breakdown": [
            {"model": m[0], "requests": m[1], "cost": round(float(m[2]), 4),
             "saved": round(float(m[3]), 4)}
            for m in model_breakdown
        ],
    }


def get_total_savings() -> float:
    conn = _ensure_db()
    row = conn.execute("SELECT COALESCE(SUM(saved), 0) FROM usage_log").fetchone()
    return round(float(row[0]), 4)
