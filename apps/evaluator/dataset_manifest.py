from __future__ import annotations

import gzip
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Small helpers to keep dataset artifacts reproducible and right-sized for MLflow logging.

DEFAULT_SAMPLE_RATIO = 0.02
DEFAULT_SAMPLE_CAP = 1000
DEFAULT_GZIP_LIMIT_MB = 100
SCHEMA_SAMPLE_FIELDS = 32


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file and return its SHA256 hex digest."""
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_jsonl_records(dataset_path: Path) -> Iterable[dict]:
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            yield json.loads(line)


def analyze_dataset(dataset_path: Path, schema_sample_fields: int = SCHEMA_SAMPLE_FIELDS) -> Tuple[int, Dict[str, int], List[str]]:
    """Count rows/splits and collect a small schema sample."""
    total_rows = 0
    split_counts: Dict[str, int] = {}
    schema_fields: List[str] = []

    for record in _iter_jsonl_records(dataset_path):
        total_rows += 1
        split = record.get("split", "default")
        split_counts[split] = split_counts.get(split, 0) + 1
        if len(schema_fields) < schema_sample_fields:
            for key in record.keys():
                if key not in schema_fields:
                    schema_fields.append(key)
                if len(schema_fields) >= schema_sample_fields:
                    break

    return total_rows, split_counts, schema_fields


def _calc_sample_targets(split_counts: Dict[str, int], ratio: float, cap: int) -> Dict[str, int]:
    """Decide how many rows to sample per split under a total cap."""
    targets = {split: max(1, int(count * ratio)) for split, count in split_counts.items() if count > 0}
    total_target = sum(targets.values())
    if total_target <= cap or total_target == 0:
        return targets

    # Scale down proportionally, then trim the largest buckets until we are within cap.
    scale = cap / total_target
    for split, target in list(targets.items()):
        targets[split] = max(1, int(target * scale))

    while sum(targets.values()) > cap:
        largest_split = max(targets, key=targets.get)
        if targets[largest_split] > 1:
            targets[largest_split] -= 1
        else:
            break

    return targets


def write_stratified_sample(
    dataset_path: Path,
    output_path: Path,
    split_counts: Dict[str, int],
    ratio: float = DEFAULT_SAMPLE_RATIO,
    cap: int = DEFAULT_SAMPLE_CAP,
    seed: int = 13,
) -> int:
    """Write a stratified JSONL sample, returning the number of rows written."""
    targets = _calc_sample_targets(split_counts, ratio, cap)
    if not targets:
        return 0

    random.seed(seed)
    seen_per_split: Dict[str, int] = {split: 0 for split in targets}
    reservoirs: Dict[str, List[dict]] = {split: [] for split in targets}

    for record in _iter_jsonl_records(dataset_path):
        split = record.get("split", "default")
        target = targets.get(split)
        if not target:
            continue

        seen_per_split[split] += 1
        seen = seen_per_split[split]
        bucket = reservoirs[split]

        if len(bucket) < target:
            bucket.append(record)
        else:
            index = random.randrange(seen)
            if index < target:
                bucket[index] = record

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for split in sorted(reservoirs):
            for record in reservoirs[split]:
                handle.write(json.dumps(record))
                handle.write("\n")

    return sum(len(bucket) for bucket in reservoirs.values())


def write_gzip_snapshot(dataset_path: Path, output_path: Path, max_mb: int = DEFAULT_GZIP_LIMIT_MB) -> Tuple[bool, str | None, str | None]:
    """
    Write a gzip snapshot of the dataset.
    Returns (has_snapshot, gzip_sha256, note_if_removed).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with dataset_path.open("rb") as source, gzip.open(output_path, "wb") as dest:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            dest.write(chunk)

    size_bytes = output_path.stat().st_size
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        output_path.unlink(missing_ok=True)
        return False, None, f"Snapshot exceeded {max_mb} MB compressed; omitted to protect store size."

    return True, compute_sha256(output_path), None


def prepare_dataset_artifacts(
    dataset_path: Path,
    output_dir: Path,
    dataset_name: str,
    version: str,
    source_uri: str,
    max_snapshot_mb: int = DEFAULT_GZIP_LIMIT_MB,
    sample_ratio: float = DEFAULT_SAMPLE_RATIO,
    sample_cap: int = DEFAULT_SAMPLE_CAP,
    seed: int = 13,
) -> dict:
    """
    Produce manifest + snapshot/sample artifacts for MLflow logging.
    Returns the manifest dict (also written to disk).
    """
    dataset_path = dataset_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    total_rows, split_counts, schema_sample = analyze_dataset(dataset_path)
    jsonl_sha256 = compute_sha256(dataset_path)

    manifest = {
        "dataset_name": dataset_name,
        "version": version,
        "source_uri": source_uri,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": total_rows,
        "splits": split_counts,
        "schema_sample": schema_sample,
        "has_snapshot": False,
        "jsonl_sha256": jsonl_sha256,
        "gzip_sha256": None,
        "sample_path": None,
        "notes": [],
    }

    snapshot_path = output_dir / "dataset.jsonl.gz"
    has_snapshot, gzip_sha, note = write_gzip_snapshot(dataset_path, snapshot_path, max_snapshot_mb)
    manifest["has_snapshot"] = has_snapshot
    manifest["gzip_sha256"] = gzip_sha
    if note:
        manifest["notes"].append(note)

    if not has_snapshot:
        sample_path = output_dir / "dataset.sample.jsonl"
        sample_rows = write_stratified_sample(
            dataset_path=dataset_path,
            output_path=sample_path,
            split_counts=split_counts,
            ratio=sample_ratio,
            cap=sample_cap,
            seed=seed,
        )
        if sample_rows > 0:
            manifest["sample_path"] = str(sample_path)
        else:
            manifest["notes"].append("Sample omitted because no eligible rows were found.")

    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return manifest
