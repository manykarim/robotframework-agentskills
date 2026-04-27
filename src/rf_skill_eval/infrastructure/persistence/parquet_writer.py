"""Parquet writer for per-run metric rows.

Used by the canary / longitudinal analysis code paths. v1 is a thin
wrapper around :mod:`polars` so the data schema matches ADR-006 §Tier 2.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import polars as pl

_log = logging.getLogger(__name__)

#: Columns expected in the per-batch metrics Parquet file.
METRICS_COLUMNS: tuple[str, ...] = (
    "batch_id",
    "cell_id",
    "task_id",
    "profile_id",
    "arm",
    "replicate_idx",
    "tier",
    "metric_id",
    "metric_family",
    "value",
    "session_id",
    "cc_version",
    "model_name",
    "computed_at",
)


def write_metrics(rows: list[dict[str, Any]], target: Path) -> Path:
    """Serialise ``rows`` to a Parquet file at ``target``.

    The caller is responsible for ensuring each row carries the
    :data:`METRICS_COLUMNS` keys; missing keys become nulls.
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        empty = pl.DataFrame({c: [] for c in METRICS_COLUMNS})
        empty.write_parquet(target)
        return target

    df = pl.DataFrame(rows)
    missing = [c for c in METRICS_COLUMNS if c not in df.columns]
    for col in missing:
        df = df.with_columns(pl.lit(None).alias(col))
    df = df.select(list(METRICS_COLUMNS))
    df.write_parquet(target, compression="snappy")
    _log.info("Wrote %d metric rows to %s", df.height, target)
    return target
