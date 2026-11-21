"""Append-only, hash-chained trial registry.

Every parameter set you evaluate is a trial, including the ones you discard.
`n_trials()` feeds the deflated Sharpe ratio so selection bias is priced in.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Registry:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def log_trial(self, family: str, name: str, params: dict, metrics: dict) -> dict:
        recs = self._records()
        body = {
            "seq": len(recs),
            "prev": recs[-1]["hash"] if recs else "0" * 64,
            "ts": time.time(),
            "family": family,
            "name": name,
            "params": params,
            "metrics": metrics,
        }
        rec = {**body, "hash": _digest(body)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec

    def records(self, family: str | None = None) -> list[dict]:
        return [r for r in self._records() if family is None or r["family"] == family]

    def n_trials(self, family: str | None = None) -> int:
        return sum(1 for r in self._records() if family is None or r["family"] == family)

    def verify(self) -> bool:
        prev = "0" * 64
        for i, rec in enumerate(self._records()):
            body = {k: v for k, v in rec.items() if k != "hash"}
            if body["seq"] != i or body["prev"] != prev or _digest(body) != rec["hash"]:
                return False
            prev = rec["hash"]
        return True
