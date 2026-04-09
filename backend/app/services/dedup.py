from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SurroundingActivity


def dedup_activities(
    db: Session, raw_activities: list
) -> tuple[list, list]:
    """Deduplicate raw activities against existing DB records.

    Args:
        db: Database session
        raw_activities: List of RawActivity objects from collectors

    Returns:
        (new_activities, duplicate_activities) — deduplicated lists
    """
    # Batch-level dedup: same source+source_id only keep first
    seen: set[str] = set()
    batch_deduped: list = []
    for act in raw_activities:
        key = f"{act.source}:{act.source_id}"
        if key in seen:
            continue
        seen.add(key)
        batch_deduped.append(act)

    # DB-level dedup: check existing records
    if not batch_deduped:
        return [], []

    # Query existing source+source_id pairs
    sources = list({act.source for act in batch_deduped})
    existing_pairs: set[str] = set()
    if sources:
        rows = (
            db.query(SurroundingActivity.source, SurroundingActivity.source_id)
            .filter(
                SurroundingActivity.source.in_(sources),
                SurroundingActivity.source_id.isnot(None),
            )
            .all()
        )
        existing_pairs = {f"{r.source}:{r.source_id}" for r in rows if r.source_id}

    new_list: list = []
    dup_list: list = []
    for act in batch_deduped:
        key = f"{act.source}:{act.source_id}"
        if key in existing_pairs:
            dup_list.append(act)
        else:
            new_list.append(act)

    return new_list, dup_list
